"""
Router Agent - FastAPI 메인 애플리케이션
Multi-Agent 시스템의 Orchestrator
"""

import os
import logging
import time
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import httpx

from .config import get_settings
from .intent_classifier import IntentClassifier
from .agent_registry import AgentRegistry
from .models import WebhookPayload, RouterResponse
from .cache import CacheManager
from .db_manager import DatabaseManager
from .metrics import (
    track_request_metrics,
    track_classification,
    track_agent_call,
    get_metrics_response,
    router_classification_confidence
)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI 앱 초기화
app = FastAPI(
    title="Router Agent",
    description="Multi-Agent 시스템의 중앙 라우터",
    version="1.0.0"
)

# 설정 로드
settings = get_settings()

# Redis 캐시 매니저 초기화
cache_manager = CacheManager(
    host=settings.redis_host,
    port=settings.redis_port,
    db=settings.redis_db,
    password=settings.redis_password
)

# PostgreSQL DB 매니저 초기화
db_manager = DatabaseManager(
    host=settings.db_host,
    port=settings.db_port,
    database=settings.db_name,
    user=settings.db_user,
    password=settings.db_password
)

# 컴포넌트 초기화
intent_classifier = IntentClassifier(
    api_key=settings.openai_api_key,
    model=settings.openai_model,
    cache_manager=cache_manager
)
agent_registry = AgentRegistry(
    sdb_agent_url=settings.sdb_agent_url,
    cache_manager=cache_manager
)

logger.info("Router Agent initialized successfully")


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "service": "Router Agent",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/metrics")
async def metrics():
    """Prometheus 메트릭 엔드포인트"""
    return get_metrics_response()


@app.get("/health")
async def health_check():
    """
    Router 헬스 체크 및 연결된 Agent 상태 확인
    """
    try:
        # 모든 Agent 헬스 체크
        agent_health = await agent_registry.health_check_all()
        
        # 전체 상태 판단
        all_healthy = all(agent_health.values())
        
        return {
            "status": "healthy" if all_healthy else "degraded",
            "timestamp": datetime.now().isoformat(),
            "agents": agent_health,
            "router_version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )


@app.get("/agents")
async def list_agents():
    """
    사용 가능한 Agent 목록 조회
    """
    try:
        agents = agent_registry.list_agents()
        
        return {
            "agents": [
                {
                    "name": agent.name,
                    "description": agent.description,
                    "capabilities": agent.capabilities,
                    "service_url": agent.service_url
                }
                for agent in agents
            ],
            "total": len(agents)
        }
    except Exception as e:
        logger.error(f"Failed to list agents: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhook")
@track_request_metrics("webhook")
async def route_webhook(request: Request):
    """
    Jira Webhook을 받아서 적절한 Agent로 라우팅

    프로세스:
    1. Webhook 페이로드 수신
    2. Intent Classification (LLM)
    3. 적절한 Agent 선택
    4. Agent 호출 및 결과 반환
    """
    start_time = time.time()
    request_id = None

    try:
        # 페이로드 파싱
        payload = await request.json()

        if not payload:
            raise HTTPException(status_code=400, detail="Empty payload")

        issue = payload.get('issue', {})
        issue_key = issue.get('key', 'UNKNOWN')
        webhook_event = payload.get('webhookEvent')

        logger.info(f"Received webhook for issue: {issue_key}")
        logger.debug(f"Payload: {payload}")

        # DB: 요청 이력 생성
        request_id = db_manager.create_request(
            issue_key=issue_key,
            webhook_event=webhook_event,
            payload=payload
        )

        # 1. Intent Classification
        classification = intent_classifier.classify_issue(issue)
        agent_name = classification.get('agent')
        confidence = classification.get('confidence', 0.0)
        reasoning = classification.get('reasoning', '')
        cached = classification.get('cached', False)

        # 신뢰도 메트릭 기록
        router_classification_confidence.observe(confidence)

        logger.info(f"Classified as {agent_name} (confidence: {confidence:.2f})")

        # DB: 분류 결과 저장
        db_manager.create_classification(
            request_id=request_id,
            issue_key=issue_key,
            classified_agent=agent_name,
            confidence=confidence,
            reasoning=reasoning,
            cached=cached
        )
        
        # 신뢰도가 너무 낮으면 경고
        if confidence < settings.classification_confidence_threshold:
            logger.warning(f"Low confidence classification: {confidence:.2f}")
            return JSONResponse({
                "status": "uncertain",
                "issue_key": issue_key,
                "classification": classification,
                "message": "분류 신뢰도가 낮아 처리하지 않았습니다."
            }, status_code=200)
        
        # 2. Agent 정보 조회
        agent = agent_registry.get_agent(agent_name)
        if not agent:
            raise HTTPException(
                status_code=404,
                detail=f"Agent not found: {agent_name}"
            )
        
        # 3. Agent 헬스 체크
        is_healthy = await agent_registry.health_check(agent_name)
        if not is_healthy:
            raise HTTPException(
                status_code=503,
                detail=f"Agent {agent_name} is not available"
            )
        
        # 4. Agent 호출 (메트릭 추적 포함)
        logger.info(f"Routing to {agent_name} at {agent.service_url}")
        
        @track_agent_call(agent_name)
        async def call_agent():
            async with httpx.AsyncClient(timeout=agent.timeout) as client:
                response = await client.post(
                    f"{agent.service_url}/process",
                    json={
                        "issue": issue,
                        "classification": classification,
                        "metadata": {
                            "routed_at": datetime.now().isoformat(),
                            "router_version": "1.0.0",
                            "original_webhook_event": payload.get('webhookEvent')
                        }
                    }
                )
                
                response.raise_for_status()
                return response.json()
        
        result = await call_agent()

        logger.info(f"Agent {agent_name} completed: {result.get('status')}")

        # DB: 성능 메트릭 저장
        total_duration = time.time() - start_time
        db_manager.create_performance_metric(
            request_id=request_id,
            agent_name='router-agent',
            metric_type='latency',
            metric_value=total_duration,
            metadata={'endpoint': 'webhook', 'agent': agent_name}
        )

        # DB: 요청 상태 업데이트
        db_manager.update_request_status(request_id, 'completed')

        # 5. 결과 반환
        return JSONResponse({
            "status": "success",
            "issue_key": issue_key,
            "agent": agent_name,
            "classification": classification,
            "request_id": request_id,
            "result": result
        })
    
    except httpx.HTTPStatusError as e:
        logger.error(f"Agent returned error: {e.response.status_code} - {e.response.text}")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Agent error: {e.response.text}"
        )
    
    except httpx.TimeoutException:
        logger.error(f"Agent timeout after {agent.timeout}s")
        raise HTTPException(
            status_code=504,
            detail="Agent timeout"
        )
    
    except Exception as e:
        logger.error(f"Routing error: {str(e)}", exc_info=True)

        # DB: 실패 상태 업데이트
        if request_id:
            db_manager.update_request_status(request_id, 'failed')

        raise HTTPException(status_code=500, detail=str(e))


@app.post("/test-classification")
async def test_classification(request: Request):
    """
    Intent Classification 테스트용 엔드포인트
    실제 Agent 호출 없이 분류만 수행
    """
    try:
        payload = await request.json()
        issue = payload.get('issue', {})
        
        classification = intent_classifier.classify_issue(issue)
        
        return {
            "classification": classification,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Classification test failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)

