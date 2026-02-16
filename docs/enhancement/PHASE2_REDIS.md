# Phase 2: Redis 캐싱 통합

## 문서 정보
- **Phase**: 2 / 4
- **예상 기간**: 2주 (Week 3-4)
- **난이도**: ⭐⭐⭐⭐ (중상)
- **선행 요구사항**: Phase 1 완료 (모니터링 시스템 운영 중)

---

## 목차
1. [개요](#개요)
2. [캐싱 전략](#캐싱-전략)
3. [Redis 배포](#redis-배포)
4. [Router Agent 캐싱](#router-agent-캐싱)
5. [SDB Agent 캐싱](#sdb-agent-캐싱)
6. [캐시 무효화 전략](#캐시-무효화-전략)
7. [성능 측정](#성능-측정)
8. [테스트 및 검증](#테스트-및-검증)
9. [트러블슈팅](#트러블슈팅)

---

## 개요

### 목표
- Bitbucket API 호출 70% 감소
- LLM API 비용 50% 절감
- 평균 응답 시간 50% 단축

### 예상 효과

| 항목 | 현재 | 목표 | 개선율 |
|------|------|------|--------|
| Bitbucket API 호출 | 100회/일 | 30회/일 | 70% ↓ |
| LLM API 비용 | $100/월 | $50/월 | 50% ↓ |
| 평균 응답 시간 | 5초 | 2.5초 | 50% ↓ |
| 캐시 히트율 | 0% | 60%+ | - |

### 캐싱 대상

1. **Router Agent**
   - Intent Classification 결과
   - Agent 헬스 체크 결과

2. **SDB Agent**
   - Bitbucket 저장소 정보
   - Bitbucket 브랜치 목록
   - Bitbucket 파일 내용 (읽기 전용)
   - LLM 코드 생성 결과 (유사 요청)

---

## 캐싱 전략

### TTL (Time To Live) 설정

| 캐시 유형 | TTL | 이유 |
|---------|-----|------|
| Bitbucket 저장소 정보 | 5분 | 자주 변경되지 않음 |
| Bitbucket 브랜치 목록 | 1분 | 실시간성 필요 |
| Bitbucket 파일 내용 | 5분 | 읽기 전용 조회 |
| Intent Classification | 24시간 | 동일 이슈는 드물지만 패턴 유사 |
| LLM 코드 생성 | 24시간 | 유사 요청 대응 |
| Agent 헬스 체크 | 30초 | 실시간 상태 확인 필요 |

### 캐시 키 설계

```python
# Intent Classification
key = f"classification:{hash(issue_summary + issue_description)}"

# Bitbucket 저장소
key = f"bitbucket:repo:{workspace}:{repository}"

# Bitbucket 브랜치 목록
key = f"bitbucket:branches:{workspace}:{repository}"

# Bitbucket 파일
key = f"bitbucket:file:{workspace}:{repository}:{branch}:{file_path_hash}"

# LLM 코드 생성
key = f"llm:code:{hash(prompt)}"

# Agent 헬스 체크
key = f"agent:health:{agent_name}"
```

### 캐시 무효화 정책

| 이벤트 | 무효화 대상 | 방법 |
|-------|-----------|------|
| PR 머지 | 해당 브랜치 파일 캐시 | DELETE 패턴 매칭 |
| 브랜치 삭제 | 브랜치 관련 모든 캐시 | DELETE 패턴 매칭 |
| Agent 재시작 | Agent 헬스 체크 캐시 | 자동 만료 (TTL) |
| 수동 무효화 | 특정 키 또는 패턴 | CLI 도구 제공 |

---

## Redis 배포

### 1. Redis ConfigMap

**파일**: `helm/multi-agent-system/templates/redis/configmap.yaml`

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: redis-config
  namespace: {{ .Values.global.namespace }}
  labels:
    app: redis
data:
  redis.conf: |
    # 네트워크
    bind 0.0.0.0
    protected-mode yes
    port 6379

    # 메모리 관리
    maxmemory 512mb
    maxmemory-policy allkeys-lru  # LRU 정책으로 오래된 키 삭제

    # 지속성 (선택)
    save ""  # RDB 스냅샷 비활성화 (캐시 용도이므로)
    appendonly no  # AOF 비활성화

    # 로깅
    loglevel notice
    logfile ""

    # 클라이언트
    timeout 300
    tcp-keepalive 60

    # 보안 (프로덕션에서는 requirepass 설정 권장)
    # requirepass your-strong-password
```

### 2. Redis Deployment

**파일**: `helm/multi-agent-system/templates/redis/deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: {{ .Values.global.namespace }}
  labels:
    app: redis
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
        - name: redis
          image: redis:7.2-alpine
          command:
            - redis-server
            - /etc/redis/redis.conf
          ports:
            - containerPort: 6379
              name: redis
          volumeMounts:
            - name: config
              mountPath: /etc/redis
            - name: data
              mountPath: /data
          resources:
            requests:
              cpu: 250m
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 512Mi
          livenessProbe:
            tcpSocket:
              port: 6379
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            exec:
              command:
                - redis-cli
                - ping
            initialDelaySeconds: 5
            periodSeconds: 5
      volumes:
        - name: config
          configMap:
            name: redis-config
        - name: data
          persistentVolumeClaim:
            claimName: redis-pvc
```

### 3. Redis Service

**파일**: `helm/multi-agent-system/templates/redis/service.yaml`

```yaml
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: {{ .Values.global.namespace }}
  labels:
    app: redis
spec:
  type: ClusterIP
  ports:
    - port: 6379
      targetPort: 6379
      protocol: TCP
      name: redis
  selector:
    app: redis
```

### 4. Redis PVC

**파일**: `helm/multi-agent-system/templates/redis/pvc.yaml`

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: redis-pvc
  namespace: {{ .Values.global.namespace }}
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
  {{- if .Values.redis.storageClassName }}
  storageClassName: {{ .Values.redis.storageClassName }}
  {{- end }}
```

---

## Router Agent 캐싱

### 1. Cache Manager 구현

**파일**: `router-agent/app/cache.py` (신규)

```python
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
            cache_key = self._cache._ generate_key(
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
```

### 2. Intent Classifier 수정

**파일**: `router-agent/app/intent_classifier.py` (수정)

```python
from .cache import CacheManager, cache_classification

class IntentClassifier:
    def __init__(self, api_key: str, model: str):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self._cache = CacheManager()  # 캐시 매니저 추가

    @cache_classification(ttl=86400)  # 24시간 캐싱
    def classify_issue(self, issue: Dict) -> Dict[str, any]:
        """
        Jira 이슈 분류 (캐싱 적용)
        """
        # 기존 분류 로직
        # ...
```

### 3. Agent Registry 수정 (헬스 체크 캐싱)

**파일**: `router-agent/app/agent_registry.py` (수정)

```python
from .cache import CacheManager

class AgentRegistry:
    def __init__(self, sdb_agent_url: str):
        # 기존 초기화
        self._cache = CacheManager()

    async def health_check(self, agent_name: str) -> bool:
        """Agent 헬스 체크 (캐싱 적용)"""
        cache_key = f"agent:health:{agent_name}"

        # 캐시 조회
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached.get('healthy', False)

        # 실제 헬스 체크
        agent = self.get_agent(agent_name)
        if not agent:
            return False

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(agent.health_check_url)
                is_healthy = response.status_code == 200

            # 캐시 저장 (30초)
            self._cache.set(cache_key, {"healthy": is_healthy}, ttl=30)

            return is_healthy
        except Exception as e:
            logger.error(f"헬스 체크 실패 ({agent_name}): {str(e)}")
            return False
```

### 4. 환경 변수 추가

**파일**: `helm/multi-agent-system/values.yaml` (수정)

```yaml
routerAgent:
  env:
    # 기존 env...
    redisHost: "redis"
    redisPort: 6379
    redisDB: 0
    # redisPassword: ""  # Secret으로 관리
```

**파일**: `router-agent/app/config.py` (수정)

```python
class Settings(BaseSettings):
    # 기존 설정...

    # Redis 설정
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
```

### 5. Requirements 업데이트

**파일**: `router-agent/requirements.txt` (추가)

```txt
redis==5.0.1
```

---

## SDB Agent 캐싱

### 1. Cache Manager 구현

**파일**: `sdb-agent/app/cache_manager.py` (신규)

```python
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
```

### 2. Bitbucket API 클래스 수정

**파일**: `sdb-agent/app/bitbucket_api.py` (수정)

```python
from app.cache_manager import CacheManager, cache_bitbucket_api

class BitbucketAPI:
    def __init__(self, url: str, username: str, access_token: str, workspace: str, repository: str):
        # 기존 초기화
        self._cache = CacheManager()  # 캐시 매니저 추가

    @cache_bitbucket_api(api_type='repo', ttl=300)  # 5분 캐싱
    def validate_token(self):
        """토큰 검증 (캐싱 적용)"""
        # 기존 코드
        pass

    @cache_bitbucket_api(api_type='branches', ttl=60)  # 1분 캐싱
    def get_branches(self):
        """브랜치 목록 조회 (캐싱 적용)"""
        # 기존 코드
        pass

    @cache_bitbucket_api(api_type='file', ttl=300)  # 5분 캐싱
    def get_file_content(self, branch: str, file_path: str):
        """파일 내용 조회 (캐싱 적용)"""
        # 기존 코드
        pass

    # 쓰기 작업은 캐싱하지 않음
    def create_branch(self, branch_name: str, from_branch: str = 'master'):
        """브랜치 생성 - 캐싱 제외"""
        result = # 기존 코드

        # 브랜치 목록 캐시 무효화
        self._cache.delete_pattern(f"bitbucket:branches:{self.workspace}:{self.repository}*")

        return result

    def commit_file(self, branch: str, file_path: str, content: str, message: str):
        """파일 커밋 - 캐싱 제외"""
        result = # 기존 코드

        # 해당 파일 캐시 무효화
        cache_key = f"bitbucket:file:{self.workspace}:{self.repository}:{branch}:{file_path}"
        self._cache.delete_pattern(cache_key + "*")

        return result
```

### 3. LLM Handler 수정

**파일**: `sdb-agent/app/llm_handler.py` (수정)

```python
from app.cache_manager import CacheManager, cache_llm_response

class LLMHandler:
    def __init__(self):
        # 기존 초기화
        self._cache = CacheManager()

    @cache_llm_response(ttl=86400)  # 24시간 캐싱
    def generate_code(self, prompt: str, **kwargs):
        """코드 생성 (캐싱 적용)"""
        # 기존 LLM 호출 코드
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            **kwargs
        )

        result = {
            "content": response.choices[0].message.content,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        }

        return result
```

### 4. 환경 변수 추가

**파일**: `sdb-agent/app/main.py` (수정)

```python
import os

# Redis 설정
REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
REDIS_DB = int(os.getenv('REDIS_DB', '0'))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)
```

### 5. Requirements 업데이트

**파일**: `sdb-agent/requirements.txt` (추가)

```txt
redis==5.0.1
```

---

## 캐시 무효화 전략

### 수동 캐시 무효화 도구

**파일**: `scripts/clear-cache.sh` (신규)

```bash
#!/bin/bash
# Redis 캐시 수동 삭제 도구

set -e

NAMESPACE="${NAMESPACE:-agent-system}"

echo "Redis 캐시 관리 도구"
echo "===================="
echo ""
echo "1. 전체 캐시 삭제"
echo "2. Intent Classification 캐시 삭제"
echo "3. Bitbucket API 캐시 삭제"
echo "4. LLM 응답 캐시 삭제"
echo "5. 특정 패턴 삭제"
echo "6. 캐시 통계 조회"
echo ""
read -p "선택 (1-6): " choice

REDIS_POD=$(kubectl get pod -n $NAMESPACE -l app=redis -o jsonpath='{.items[0].metadata.name}')

case $choice in
  1)
    echo "전체 캐시를 삭제합니다..."
    kubectl exec -n $NAMESPACE $REDIS_POD -- redis-cli FLUSHDB
    echo "✓ 완료"
    ;;
  2)
    echo "Intent Classification 캐시를 삭제합니다..."
    kubectl exec -n $NAMESPACE $REDIS_POD -- redis-cli --scan --pattern "classification:*" | xargs kubectl exec -n $NAMESPACE $REDIS_POD -- redis-cli DEL
    echo "✓ 완료"
    ;;
  3)
    echo "Bitbucket API 캐시를 삭제합니다..."
    kubectl exec -n $NAMESPACE $REDIS_POD -- redis-cli --scan --pattern "bitbucket:*" | xargs kubectl exec -n $NAMESPACE $REDIS_POD -- redis-cli DEL
    echo "✓ 완료"
    ;;
  4)
    echo "LLM 응답 캐시를 삭제합니다..."
    kubectl exec -n $NAMESPACE $REDIS_POD -- redis-cli --scan --pattern "llm:*" | xargs kubectl exec -n $NAMESPACE $REDIS_POD -- redis-cli DEL
    echo "✓ 완료"
    ;;
  5)
    read -p "패턴 입력: " pattern
    echo "$pattern 패턴의 캐시를 삭제합니다..."
    kubectl exec -n $NAMESPACE $REDIS_POD -- redis-cli --scan --pattern "$pattern" | xargs kubectl exec -n $NAMESPACE $REDIS_POD -- redis-cli DEL
    echo "✓ 완료"
    ;;
  6)
    echo "캐시 통계:"
    kubectl exec -n $NAMESPACE $REDIS_POD -- redis-cli INFO stats | grep -E "keyspace_hits|keyspace_misses"
    echo ""
    echo "키 개수:"
    kubectl exec -n $NAMESPACE $REDIS_POD -- redis-cli DBSIZE
    ;;
  *)
    echo "잘못된 선택입니다."
    exit 1
    ;;
esac
```

---

## 성능 측정

### 캐시 메트릭 추가

**파일**: `router-agent/app/metrics.py` (추가)

```python
from prometheus_client import Counter, Gauge

# 캐시 메트릭
cache_hits_total = Counter(
    'cache_hits_total',
    'Total cache hits',
    ['cache_type']  # classification, agent_health
)

cache_misses_total = Counter(
    'cache_misses_total',
    'Total cache misses',
    ['cache_type']
)

cache_size_bytes = Gauge(
    'cache_size_bytes',
    'Current cache size in bytes'
)
```

**파일**: `router-agent/app/cache.py` (수정)

```python
from .metrics import cache_hits_total, cache_misses_total

def get(self, key: str) -> Optional[Dict]:
    # ...
    if value:
        cache_hits_total.labels(cache_type='classification').inc()
        return json.loads(value)
    else:
        cache_misses_total.labels(cache_type='classification').inc()
        return None
```

### Grafana 대시보드 패널 추가

```promql
# 캐시 히트율
sum(rate(cache_hits_total[5m])) / (sum(rate(cache_hits_total[5m])) + sum(rate(cache_misses_total[5m]))) * 100

# API 호출 감소율
(1 - rate(sdb_bitbucket_api_calls_total{status="success"}[1h])) * 100
```

---

## 테스트 및 검증

### 1. Redis 연결 테스트

```bash
# Redis Pod 접속
kubectl exec -it <redis-pod> -n agent-system -- redis-cli

# PING 테스트
127.0.0.1:6379> PING
PONG

# 키 조회
127.0.0.1:6379> KEYS *

# 통계 확인
127.0.0.1:6379> INFO stats
```

### 2. 캐싱 동작 확인

```bash
# 동일한 요청 2번 전송
for i in 1 2; do
  curl -X POST http://router-agent/webhook \
    -H "Content-Type: application/json" \
    -d @test-webhook.json
  echo ""
done

# Router Agent 로그 확인
# 첫 번째: "캐시 MISS"
# 두 번째: "캐시 HIT"
kubectl logs -f <router-pod> -n agent-system | grep "캐시"
```

### 3. 성능 비교

**테스트 스크립트**: `test/performance-test.sh`

```bash
#!/bin/bash

echo "캐싱 비활성화 상태 테스트..."
# Redis 일시 중지
kubectl scale deployment redis --replicas=0 -n agent-system
sleep 10

# 10회 요청, 시간 측정
time for i in {1..10}; do
  curl -s -X POST http://router-agent/webhook -d @test-webhook.json > /dev/null
done

echo ""
echo "캐싱 활성화 상태 테스트..."
# Redis 재시작
kubectl scale deployment redis --replicas=1 -n agent-system
sleep 20

# 첫 요청 (캐시 MISS)
curl -s -X POST http://router-agent/webhook -d @test-webhook.json > /dev/null

# 10회 요청, 시간 측정 (캐시 HIT)
time for i in {1..10}; do
  curl -s -X POST http://router-agent/webhook -d @test-webhook.json > /dev/null
done
```

---

## 검증 체크리스트

- [ ] Redis가 배포되고 정상 동작함
- [ ] Router Agent가 Redis에 연결됨
- [ ] SDB Agent가 Redis에 연결됨
- [ ] Intent Classification 캐싱 동작 확인
- [ ] Bitbucket API 캐싱 동작 확인
- [ ] LLM 응답 캐싱 동작 확인
- [ ] 캐시 히트율 60% 이상
- [ ] API 호출 횟수 70% 감소 확인
- [ ] 응답 시간 50% 단축 확인
- [ ] 캐시 메트릭이 Prometheus에 수집됨
- [ ] Grafana 대시보드에 캐시 메트릭 표시됨

---

## 트러블슈팅

### 문제 1: Redis 연결 실패

**증상**: Agent 로그에 "Redis 연결 실패" 메시지

**해결**:
```bash
# Redis Pod 상태 확인
kubectl get pod -n agent-system -l app=redis

# Redis 서비스 확인
kubectl get svc redis -n agent-system

# 네트워크 연결 테스트
kubectl exec -it <agent-pod> -n agent-system -- nc -zv redis 6379
```

### 문제 2: 캐시가 동작하지 않음

**증상**: 모든 요청이 캐시 MISS

**해결**:
```bash
# Redis 로그 확인
kubectl logs -f <redis-pod> -n agent-system

# Agent 로그에서 캐시 키 확인
kubectl logs -f <agent-pod> -n agent-system | grep "캐시"

# Redis에서 직접 키 확인
kubectl exec -it <redis-pod> -n agent-system -- redis-cli KEYS "*"
```

### 문제 3: 메모리 부족

**증상**: Redis가 OOMKilled 상태

**해결**:
```yaml
# Redis Deployment 수정: 메모리 limit 증가
resources:
  limits:
    memory: 1Gi  # 512Mi → 1Gi
```

---

## 다음 단계

Phase 2 완료 후:
1. ✅ 캐시 히트율 모니터링 (1주일)
2. ✅ TTL 최적화
3. → [PHASE3_POSTGRESQL.md](./PHASE3_POSTGRESQL.md) 진행

---

**문서 버전**: 1.0.0
**최종 업데이트**: 2025-10-22
