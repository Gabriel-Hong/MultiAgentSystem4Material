"""
Agent Registry - Agent 목록 및 메타데이터 관리
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
import httpx

logger = logging.getLogger(__name__)


@dataclass
class AgentInfo:
    """Agent 정보"""
    name: str
    service_url: str
    capabilities: List[str]
    health_check_url: str
    timeout: int = 300
    description: str = ""


class AgentRegistry:
    """Agent 레지스트리"""

    def __init__(self, sdb_agent_url: str = "http://sdb-agent-svc:5000", cache_manager=None):
        """
        Args:
            sdb_agent_url: SDB Agent 서비스 URL
            cache_manager: CacheManager 인스턴스 (선택)
        """
        self._cache = cache_manager
        self.agents: Dict[str, AgentInfo] = {
            "sdb-agent": AgentInfo(
                name="sdb-agent",
                service_url=sdb_agent_url,
                capabilities=["sdb_generation", "material_db_addition", "code_modification"],
                health_check_url=f"{sdb_agent_url}/health",
                timeout=300,
                description="SDB 개발 및 Material DB 추가 자동화 Agent"
            ),
            # 향후 추가될 Agent들
            # "code-review-agent": AgentInfo(...),
            # "test-generation-agent": AgentInfo(...),
        }
    
    def get_agent(self, agent_name: str) -> Optional[AgentInfo]:
        """
        Agent 정보 조회
        
        Args:
            agent_name: Agent 이름
            
        Returns:
            AgentInfo 또는 None
        """
        agent = self.agents.get(agent_name)
        if agent:
            logger.info(f"Agent found: {agent_name}")
        else:
            logger.warning(f"Agent not found: {agent_name}")
        return agent
    
    def list_agents(self) -> List[AgentInfo]:
        """
        모든 Agent 목록 반환
        
        Returns:
            Agent 정보 리스트
        """
        return list(self.agents.values())
    
    async def health_check(self, agent_name: str) -> bool:
        """
        특정 Agent 헬스 체크 (캐싱 적용)

        Args:
            agent_name: Agent 이름

        Returns:
            건강 상태 (True/False)
        """
        # 캐시 조회
        cache_key = f"agent:health:{agent_name}"
        if self._cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Health check 캐시 HIT: {agent_name}")
                return cached.get('healthy', False)

        agent = self.get_agent(agent_name)
        if not agent:
            return False

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(agent.health_check_url)
                is_healthy = response.status_code == 200

                if is_healthy:
                    logger.info(f"Agent {agent_name} is healthy")
                else:
                    logger.warning(f"Agent {agent_name} returned status {response.status_code}")

                # 캐시 저장 (30초)
                if self._cache:
                    self._cache.set(cache_key, {"healthy": is_healthy}, ttl=30)

                return is_healthy
        except Exception as e:
            logger.error(f"Health check failed for {agent_name}: {str(e)}")

            # 실패한 경우에도 짧은 시간 캐싱 (10초)
            if self._cache:
                self._cache.set(cache_key, {"healthy": False}, ttl=10)

            return False
    
    async def health_check_all(self) -> Dict[str, bool]:
        """
        모든 Agent의 헬스 체크
        
        Returns:
            Agent별 건강 상태 딕셔너리
        """
        results = {}
        
        for name in self.agents.keys():
            results[name] = await self.health_check(name)
        
        return results

