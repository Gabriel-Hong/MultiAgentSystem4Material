# Redis 캐싱 트러블슈팅 가이드

## 목차
- [연결 실패 문제](#연결-실패-문제)
- [캐시 확인 방법](#캐시-확인-방법)
- [비밀번호 설정 (선택)](#비밀번호-설정-선택)

---

## 연결 실패 문제

### 증상
Router Agent 로그에서 다음과 같은 에러 발생:
```
ERROR - Redis 연결 실패: Error 111 connecting to redis:6379. Connection refused.
WARNING - 캐싱이 비활성화됩니다.
```

### 원인
Redis의 `protected-mode yes` 설정 때문에 비밀번호 없이 외부 연결이 거부됨.

Redis는 다음 조건에서만 외부 연결을 허용:
- 비밀번호가 설정되어 있거나
- `protected-mode no`로 설정

### 진단 방법

#### 1. Redis Service 및 Endpoint 확인
```bash
# Service 확인
kubectl get svc -n agent-system | grep redis

# Service 상세 정보
kubectl describe svc redis -n agent-system

# Endpoint 확인
kubectl get endpoints redis -n agent-system

# Redis Pod 확인
kubectl get pod -n agent-system -l app=redis --show-labels
```

정상적인 경우:
```
NAME    ENDPOINTS         AGE
redis   10.244.0.7:6379   48m
```

#### 2. Redis Pod 로그 확인
```bash
kubectl logs deployment/redis -n agent-system
```

#### 3. Agent에서 Redis 연결 테스트
```bash
# Router Agent 로그에서 Redis 관련 확인
kubectl logs deployment/router-agent -n agent-system | grep -i redis

# Pod에서 직접 연결 테스트
kubectl exec -it deployment/router-agent -n agent-system -- sh -c "nc -zv redis 6379"
```

### 해결 방법

#### ConfigMap 수정
**파일**: `helm/multi-agent-system/templates/redis/configmap.yaml`

```yaml
data:
  redis.conf: |
    # 네트워크
    bind 0.0.0.0
    protected-mode no  # yes → no로 변경
    port 6379
```

#### 변경사항 적용
```bash
# 1. Helm 차트 업그레이드
helm upgrade multi-agent-system ./helm/multi-agent-system -n agent-system

# 2. Redis Pod 재시작
kubectl rollout restart deployment/redis -n agent-system

# 3. Redis 재시작 완료 대기
kubectl rollout status deployment/redis -n agent-system

# 4. Router Agent 재시작
kubectl rollout restart deployment/router-agent -n agent-system

# 5. 연결 확인 (10초 대기 후)
sleep 10
kubectl logs deployment/router-agent -n agent-system --tail=50 | grep -i redis
```

성공 시 로그:
```
INFO - Redis 연결 성공: redis:6379
```

---

## 캐시 확인 방법

### 캐싱 동작 테스트
프로젝트에 포함된 테스트 스크립트 사용:
```bash
bash scripts/test-redis-caching.sh
```

성공 시 출력:
```
첫 번째 요청: 6078ms (cached: unknown)
두 번째 요청: 14ms (cached: true)

✅ 캐싱 성공!
   - 속도 개선: 99% 향상
```

### Redis CLI로 직접 확인

#### 1. 모든 캐시 키 조회
```bash
kubectl exec -it deployment/redis -n agent-system -- redis-cli KEYS "*"
```

출력 예시:
```
classification:b10af79d9b3abcc1
classification:a2c3e4f5g6h7i8j9
```

#### 2. 특정 키의 값 확인
```bash
kubectl exec -it deployment/redis -n agent-system -- redis-cli GET "classification:b10af79d9b3abcc1"
```

출력 예시 (JSON 형태):
```json
"{\"agent\": \"sdb-agent\", \"confidence\": 0.95, \"reasoning\": \"이슈 제목과 설명에 'SDB', '재질' 키워드가 포함되어 있습니다.\"}"
```

#### 3. 캐시 통계 확인
```bash
kubectl exec -it deployment/redis -n agent-system -- redis-cli INFO stats
```

주요 지표:
```
keyspace_hits:42      # 캐시 HIT 횟수
keyspace_misses:6     # 캐시 MISS 횟수
```
히트율 = hits / (hits + misses) × 100 = 87.5%

#### 4. 메모리 사용량 확인
```bash
kubectl exec -it deployment/redis -n agent-system -- redis-cli INFO memory
```

#### 5. 대화형 CLI 사용
```bash
kubectl exec -it deployment/redis -n agent-system -- redis-cli
```

Redis CLI 내부:
```redis
127.0.0.1:6379> KEYS *
127.0.0.1:6379> GET "classification:b10af79d9b3abcc1"
127.0.0.1:6379> TTL "classification:b10af79d9b3abcc1"  # 남은 만료 시간 (초)
127.0.0.1:6379> DBSIZE  # 총 키 개수
127.0.0.1:6379> FLUSHALL  # 모든 캐시 삭제 (주의!)
127.0.0.1:6379> exit
```

### 캐시 데이터 형식 이해

#### Unicode Escape Sequence
Redis에 저장된 한글은 `\uXXXX` 형태로 표시됩니다:
```
\uc288\uc81c\ubaa9 = 슈제목
```

이는 Python `json.dumps()`의 기본 동작(`ensure_ascii=True`)입니다:
- **장점**: 모든 시스템에서 안전하게 동작, 인코딩 문제 없음
- **단점**: 사람이 읽기 어려움

애플리케이션에서 `json.loads()`로 읽을 때는 자동으로 한글로 변환됩니다.

---

## 비밀번호 설정 (선택)

현재는 Kubernetes 클러스터 내부 전용이므로 비밀번호 없이 사용해도 안전합니다.
프로덕션 환경에서 추가 보안이 필요한 경우에만 설정하세요.

### 비밀번호 설정 방법

#### 1. ConfigMap 수정
**파일**: `helm/multi-agent-system/templates/redis/configmap.yaml`

```yaml
data:
  redis.conf: |
    # 네트워크
    bind 0.0.0.0
    protected-mode yes  # 비밀번호 사용 시 yes로 변경
    port 6379

    # 보안
    requirepass your-strong-password  # 강력한 비밀번호 설정
```

#### 2. Agent 설정에 비밀번호 추가

**Router Agent**: `helm/multi-agent-system/templates/router-agent/deployment.yaml`
```yaml
env:
  - name: REDIS_PASSWORD
    value: "your-strong-password"
```

**SDB Agent**: `helm/multi-agent-system/templates/sdb-agent/deployment.yaml`
```yaml
env:
  - name: REDIS_PASSWORD
    value: "your-strong-password"
```

#### 3. Python 코드에서 비밀번호 사용

`router-agent/app/config.py`와 `router-agent/app/cache.py`는 이미 비밀번호를 지원합니다:

```python
# config.py
class Settings(BaseSettings):
    redis_password: Optional[str] = None  # 환경변수 REDIS_PASSWORD

# cache.py
cache_manager = CacheManager(
    host=settings.redis_host,
    port=settings.redis_port,
    db=settings.redis_db,
    password=settings.redis_password  # 자동으로 적용됨
)
```

#### 4. 더 안전한 방법: Kubernetes Secret 사용

```bash
# Secret 생성
kubectl create secret generic redis-secret \
  --from-literal=password='your-strong-password' \
  -n agent-system

# Deployment에서 Secret 참조
env:
  - name: REDIS_PASSWORD
    valueFrom:
      secretKeyRef:
        name: redis-secret
        key: password
```

### 비밀번호 적용 후 확인
```bash
# Redis CLI 접속 시 비밀번호 필요
kubectl exec -it deployment/redis -n agent-system -- redis-cli -a your-strong-password

# 또는 CLI 내부에서 인증
kubectl exec -it deployment/redis -n agent-system -- redis-cli
127.0.0.1:6379> AUTH your-strong-password
OK
127.0.0.1:6379> PING
PONG
```

---

## 성능 지표

### 캐싱 효과
- **첫 요청** (캐시 MISS): 약 6,000ms (LLM API 호출)
- **두 번째 요청** (캐시 HIT): 약 14ms (Redis 조회)
- **성능 향상**: 99% (434배 빠름)

### 권장 모니터링 지표
```bash
# 실시간 통계 모니터링
watch -n 1 'kubectl exec -it deployment/redis -n agent-system -- redis-cli INFO stats | grep keyspace'
```

- **히트율 목표**: 80% 이상
- **메모리 사용량**: maxmemory 설정값(512MB) 이하
- **연결 클라이언트**: Agent 수만큼 (Router + SDB)

---

## 관련 파일

- `helm/multi-agent-system/templates/redis/configmap.yaml` - Redis 설정
- `helm/multi-agent-system/templates/redis/deployment.yaml` - Redis Deployment
- `helm/multi-agent-system/templates/redis/service.yaml` - Redis Service
- `router-agent/app/cache.py` - 캐싱 매니저 구현
- `router-agent/app/config.py` - Redis 연결 설정
- `scripts/test-redis-caching.sh` - 캐싱 테스트 스크립트
