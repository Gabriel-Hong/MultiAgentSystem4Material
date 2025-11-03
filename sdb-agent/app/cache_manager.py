"""
Redis 캐싱 매니저 - SDB Agent
"""
import redis
import json
import logging
import hashlib
from typing import Optional, Any, Dict
from functools import wraps

logger = logging.getLogger(__name__)


class CacheManager:
    """Redis 캐싱 매니저 - SDB Agent용"""

    def __init__(self, host: str = 'redis', port: int = 6379, db: int = 0, password: Optional[str] = None):
        try:
            self.client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=True,
                socket_timeout=5
            )
            self.client.ping()
            logger.info(f"Redis 연결 성공: {host}:{port}")
            self.enabled = True
        except Exception as e:
            logger.error(f"Redis 연결 실패: {str(e)}")
            self.enabled = False
            self.client = None

    def get(self, key: str) -> Optional[Any]:
        """캐시 조회"""
        if not self.enabled:
            return None

        try:
            value = self.client.get(key)
            if value:
                logger.debug(f"캐시 HIT: {key}")
                return json.loads(value)
            logger.debug(f"캐시 MISS: {key}")
            return None
        except Exception as e:
            logger.error(f"캐시 조회 실패: {str(e)}")
            return None

    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """캐시 저장"""
        if not self.enabled:
            return False

        try:
            self.client.setex(key, ttl, json.dumps(value))
            logger.debug(f"캐시 저장: {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"캐시 저장 실패: {str(e)}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """패턴 삭제"""
        if not self.enabled:
            return 0

        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"캐시 패턴 삭제 실패: {str(e)}")
            return 0


def cache_bitbucket_api(api_type: str, ttl: int = 300):
    """
    Bitbucket API 호출 캐싱 데코레이터

    Args:
        api_type: API 유형 (repo, branches, file 등)
        ttl: TTL (기본: 5분)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # 캐시 키 생성
            key_parts = [api_type, self.workspace, self.repository] + [str(arg) for arg in args]
            cache_key = "bitbucket:" + ":".join(key_parts)

            # 캐시 조회
            if hasattr(self, '_cache'):
                cached = self._cache.get(cache_key)
                if cached is not None:
                    logger.info(f"Bitbucket API 캐시 HIT: {api_type}")
                    return cached

            # 실제 API 호출
            result = func(self, *args, **kwargs)

            # 캐시 저장
            if hasattr(self, '_cache') and result:
                self._cache.set(cache_key, result, ttl)

            return result

        return wrapper
    return decorator


def cache_llm_response(ttl: int = 86400):
    """
    LLM 응답 캐싱 데코레이터

    Args:
        ttl: TTL (기본: 24시간)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, prompt: str, *args, **kwargs):
            # 프롬프트 해시로 캐시 키 생성
            prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]
            cache_key = f"llm:code:{prompt_hash}"

            # 캐시 조회
            if hasattr(self, '_cache'):
                cached = self._cache.get(cache_key)
                if cached is not None:
                    logger.info(f"LLM 응답 캐시 HIT")
                    return cached

            # 실제 LLM 호출
            result = func(self, prompt, *args, **kwargs)

            # 캐시 저장
            if hasattr(self, '_cache') and result:
                self._cache.set(cache_key, result, ttl)

            return result

        return wrapper
    return decorator
