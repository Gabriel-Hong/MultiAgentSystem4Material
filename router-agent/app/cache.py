"""
Redis 캐싱 매니저 - Router Agent
"""
import redis
import json
import logging
import hashlib
from typing import Optional, Any, Dict
from functools import wraps
import time

logger = logging.getLogger(__name__)


class CacheManager:
    """Redis 캐싱 매니저"""

    def __init__(self, host: str = 'redis', port: int = 6379, db: int = 0, password: Optional[str] = None):
        """
        Args:
            host: Redis 호스트
            port: Redis 포트
            db: Redis DB 번호
            password: Redis 비밀번호
        """
        try:
            self.client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            # 연결 테스트
            self.client.ping()
            logger.info(f"Redis 연결 성공: {host}:{port}")
            self.enabled = True
        except Exception as e:
            logger.error(f"Redis 연결 실패: {str(e)}")
            logger.warning("캐싱이 비활성화됩니다.")
            self.enabled = False
            self.client = None

    def _generate_key(self, prefix: str, data: Any) -> str:
        """
        캐시 키 생성

        Args:
            prefix: 키 접두사
            data: 해시할 데이터

        Returns:
            캐시 키
        """
        if isinstance(data, dict):
            data_str = json.dumps(data, sort_keys=True)
        else:
            data_str = str(data)

        data_hash = hashlib.sha256(data_str.encode()).hexdigest()[:16]
        return f"{prefix}:{data_hash}"

    def get(self, key: str) -> Optional[Dict]:
        """
        캐시에서 데이터 조회

        Args:
            key: 캐시 키

        Returns:
            캐시된 데이터 또는 None
        """
        if not self.enabled:
            return None

        try:
            value = self.client.get(key)
            if value:
                logger.debug(f"캐시 HIT: {key}")
                return json.loads(value)
            else:
                logger.debug(f"캐시 MISS: {key}")
                return None
        except Exception as e:
            logger.error(f"캐시 조회 실패 ({key}): {str(e)}")
            return None

    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """
        캐시에 데이터 저장

        Args:
            key: 캐시 키
            value: 저장할 데이터
            ttl: TTL (초)

        Returns:
            성공 여부
        """
        if not self.enabled:
            return False

        try:
            value_str = json.dumps(value)
            self.client.setex(key, ttl, value_str)
            logger.debug(f"캐시 저장: {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"캐시 저장 실패 ({key}): {str(e)}")
            return False

    def delete(self, key: str) -> bool:
        """
        캐시 삭제

        Args:
            key: 캐시 키

        Returns:
            성공 여부
        """
        if not self.enabled:
            return False

        try:
            self.client.delete(key)
            logger.debug(f"캐시 삭제: {key}")
            return True
        except Exception as e:
            logger.error(f"캐시 삭제 실패 ({key}): {str(e)}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """
        패턴과 일치하는 모든 키 삭제

        Args:
            pattern: 패턴 (예: "classification:*")

        Returns:
            삭제된 키 개수
        """
        if not self.enabled:
            return 0

        try:
            keys = self.client.keys(pattern)
            if keys:
                count = self.client.delete(*keys)
                logger.info(f"캐시 패턴 삭제: {pattern} ({count}개)")
                return count
            return 0
        except Exception as e:
            logger.error(f"캐시 패턴 삭제 실패 ({pattern}): {str(e)}")
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """
        캐시 통계 조회

        Returns:
            통계 정보
        """
        if not self.enabled:
            return {"enabled": False}

        try:
            info = self.client.info('stats')
            return {
                "enabled": True,
                "keyspace_hits": info.get('keyspace_hits', 0),
                "keyspace_misses": info.get('keyspace_misses', 0),
                "hit_rate": self._calculate_hit_rate(info),
                "used_memory": self.client.info('memory').get('used_memory_human'),
                "connected_clients": self.client.info('clients').get('connected_clients')
            }
        except Exception as e:
            logger.error(f"캐시 통계 조회 실패: {str(e)}")
            return {"enabled": True, "error": str(e)}

    def _calculate_hit_rate(self, info: Dict) -> float:
        """히트율 계산"""
        hits = info.get('keyspace_hits', 0)
        misses = info.get('keyspace_misses', 0)
        total = hits + misses
        return (hits / total * 100) if total > 0 else 0.0


def cache_classification(ttl: int = 86400):
    """
    Intent Classification 결과 캐싱 데코레이터

    Args:
        ttl: TTL (기본: 24시간)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, issue: Dict, *args, **kwargs):
            # 캐시 키 생성
            cache_key = self._cache._generate_key(
                "classification",
                {
                    "summary": issue.get('fields', {}).get('summary', ''),
                    "description": issue.get('fields', {}).get('description', ''),
                    "issue_type": issue.get('fields', {}).get('issuetype', {}).get('name', '')
                }
            )

            # 캐시 조회
            cached = self._cache.get(cache_key)
            if cached:
                logger.info(f"Classification 캐시 HIT: {issue.get('key')}")
                cached['cached'] = True
                return cached

            # 캐시 미스 - 실제 분류 수행
            result = func(self, issue, *args, **kwargs)

            # 캐시 저장
            self._cache.set(cache_key, result, ttl)
            result['cached'] = False

            return result

        return wrapper
    return decorator
