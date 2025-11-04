"""
SDB 자동 생성 에이전트 - Flask 애플리케이션
Jira 이슈 기반 자동 소스코드 수정 및 PR 생성
"""

import os
import json
import logging
from flask import Flask, request, jsonify
from datetime import datetime

# 로컬 모듈 임포트
try:
    from app.config import get_settings
    from app.bitbucket_api import BitbucketAPI
    from app.llm_handler import LLMHandler
    from app.issue_processor import IssueProcessor
    from app.cache_manager import CacheManager
    from app.db_manager import DatabaseManager
    from app.metrics import (
        track_processing_time,
        get_metrics,
        sdb_pr_created_total
    )
except ImportError:
    # 직접 실행시를 위한 상대 경로 임포트
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from config import get_settings
    from bitbucket_api import BitbucketAPI
    from llm_handler import LLMHandler
    from issue_processor import IssueProcessor
    from cache_manager import CacheManager
    from db_manager import DatabaseManager
    from metrics import (
        track_processing_time,
        get_metrics,
        sdb_pr_created_total
    )

# Flask 애플리케이션 초기화
app = Flask(__name__)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 현재 작업 디렉토리 로그 출력
logger.info(f"Flask 애플리케이션 작업 디렉토리: {os.getcwd()}")

# 설정 로드
settings = get_settings()

# 테스트 모드 설정 (환경 변수 TEST_MODE=true 또는 DEBUG 모드에서 활성화)
TEST_MODE = settings.test_mode or settings.flask_env == 'development'
logger.info(f"테스트 모드 활성화: {TEST_MODE}")

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

# API 클라이언트 초기화
bitbucket_api = BitbucketAPI(
    url=settings.bitbucket_url,
    username=settings.bitbucket_username,
    access_token=settings.bitbucket_access_token,
    workspace=settings.bitbucket_workspace,
    repository=settings.bitbucket_repository,
    cache_manager=cache_manager
)

# 토큰 유효성 검증
if settings.bitbucket_access_token:
    is_valid, repo_data = bitbucket_api.validate_token()
    if is_valid:
        logger.info(f"Bitbucket API 연결 성공! 저장소: {repo_data.get('name', 'Unknown')}")
    else:
        logger.warning("Bitbucket 토큰 검증 실패. 일부 기능이 제한될 수 있습니다.")
else:
    logger.warning("BITBUCKET_ACCESS_TOKEN이 설정되지 않았습니다.")

llm_handler = LLMHandler(cache_manager=cache_manager)
issue_processor = IssueProcessor(bitbucket_api, llm_handler)


@app.route('/health', methods=['GET'])
def health_check():
    """헬스 체크 엔드포인트"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'test_mode': TEST_MODE
    }), 200


@app.route('/metrics', methods=['GET'])
def metrics():
    """Prometheus 메트릭 엔드포인트"""
    from flask import Response
    metrics_data, content_type = get_metrics()
    return Response(metrics_data, mimetype=content_type)


@app.route('/process', methods=['POST'])
@track_processing_time
def process_handler():
    """
    Router Agent용 표준 처리 엔드포인트

    요청 형식:
    {
        "issue": {...},  # Jira 이슈 정보
        "classification": {...},  # Router의 분류 결과
        "metadata": {...}  # 추가 메타데이터
    }

    응답 형식:
    {
        "status": "success" | "failed",
        "issue_key": "PROJ-123",
        "result": {...},
        "agent": "sdb-agent",
        "version": "1.0.0"
    }
    """
    import time
    start_time = time.time()
    pr_status = 'failed'
    request_id = None

    try:
        payload = request.get_json()

        if not payload:
            logger.error("페이로드가 비어있습니다.")
            return jsonify({'error': '페이로드가 없습니다.'}), 400

        # Router Agent로부터 전달된 데이터 추출
        issue = payload.get('issue', {})
        classification = payload.get('classification', {})
        metadata = payload.get('metadata', {})

        issue_key = issue.get('key', 'UNKNOWN')

        # Router에서 전달된 request_id 추출 (있으면)
        # 없으면 None으로 처리 (DB 외래키 제약조건은 nullable)

        logger.info(f"Processing issue from Router: {issue_key}")
        logger.info(f"Classification: {classification}")
        logger.info(f"Metadata: {metadata}")

        # 기존 issue_processor 사용
        result = issue_processor.process_issue(issue)

        # DB: 코드 변경 이력 저장
        modified_files = result.get('modified_files', [])
        for file_info in modified_files:
            db_manager.create_code_change(
                request_id=request_id,
                issue_key=issue_key,
                file_path=file_info.get('path', ''),
                change_type=file_info.get('change_type', 'modified'),
                diff_content=file_info.get('diff'),
                branch_name=result.get('branch_name'),
                commit_hash=result.get('commit_hash'),
                pr_url=result.get('pr_url')
            )

        # DB: 성능 메트릭 저장
        processing_duration = time.time() - start_time
        db_manager.create_performance_metric(
            request_id=request_id,
            agent_name='sdb-agent',
            metric_type='latency',
            metric_value=processing_duration,
            metadata={'issue_key': issue_key}
        )

        # PR 생성 성공/실패 메트릭 기록
        if result.get('status') == 'completed' and result.get('pr_url'):
            pr_status = 'success'
            sdb_pr_created_total.labels(status='success').inc()
        else:
            pr_status = 'failed'
            sdb_pr_created_total.labels(status='failed').inc()

        return jsonify({
            'status': result.get('status', 'completed'),
            'issue_key': issue_key,
            'result': result,
            'agent': 'sdb-agent',
            'version': '1.0.0'
        }), 200

    except Exception as e:
        # 에러 발생시 PR 실패 메트릭 기록
        sdb_pr_created_total.labels(status='failed').inc()
        logger.error(f"처리 중 오류 발생: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'failed',
            'error': str(e),
            'agent': 'sdb-agent',
            'version': '1.0.0'
        }), 500


@app.route('/capabilities', methods=['GET'])
def capabilities():
    """
    Agent 기능 목록
    
    응답:
    {
        "capabilities": ["sdb_generation", "material_db_addition", ...],
        "supported_issue_types": ["SDB 개발 요청", ...],
        "version": "1.0.0"
    }
    """
    return jsonify({
        'capabilities': [
            'sdb_generation',
            'material_db_addition',
            'code_modification',
            'bitbucket_pr_creation'
        ],
        'supported_issue_types': [
            'SDB 개발 요청',
            'Material DB 추가',
            '코드 수정'
        ],
        'version': '1.0.0',
        'description': 'SDB 개발 및 Material DB 추가 자동화 Agent'
    }), 200


@app.route('/webhook', methods=['POST'])
def webhook_handler():
    """
    Jira 웹훅 핸들러 (하위 호환성 유지)
    SDB 개발 요청 이슈가 생성되면 자동으로 처리
    
    Note: 이 엔드포인트는 하위 호환성을 위해 유지됩니다.
          Multi-Agent 시스템에서는 /process 엔드포인트를 사용하세요.
    """
    try:
        # 웹훅 페이로드 파싱
        payload = request.get_json()
        
        if not payload:
            logger.error("웹훅 페이로드가 비어있습니다.")
            return jsonify({'error': '페이로드가 없습니다.'}), 400
        
        logger.info(f"웹훅 수신: {json.dumps(payload, indent=2, ensure_ascii=False)}")
        
        # 이슈 타입 확인 (SDB 개발 요청인지)
        webhook_event = payload.get('webhookEvent')
        issue = payload.get('issue', {})
        
        # 이슈 생성 이벤트이고 SDB 개발 요청인 경우에만 처리
        if webhook_event == 'jira:issue_created':
            issue_type = issue.get('fields', {}).get('issuetype', {}).get('name', '')
            
            if 'SDB' in issue_type or 'SDB 개발' in issue.get('fields', {}).get('summary', ''):
                logger.info(f"SDB 개발 요청 감지: {issue.get('key')}")
                
                # 비동기로 처리 (실제 환경에서는 Celery 등 사용 권장)
                result = issue_processor.process_issue(issue)
                
                return jsonify({
                    'status': 'processing',
                    'issue_key': issue.get('key'),
                    'result': result
                }), 200
            else:
                logger.info("SDB 개발 요청이 아닙니다. 무시합니다.")
                return jsonify({'status': 'ignored', 'reason': 'Not SDB issue'}), 200
        
        return jsonify({'status': 'ignored', 'reason': 'Not issue created event'}), 200
        
    except Exception as e:
        logger.error(f"웹훅 처리 중 오류 발생: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Railway 프로덕션 환경용 포트 설정
    port = int(os.environ.get('PORT', settings.port))
    app.run(host='0.0.0.0', port=port, debug=False)
