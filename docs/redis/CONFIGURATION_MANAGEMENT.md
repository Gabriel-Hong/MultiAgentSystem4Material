# Redis 설정 관리 가이드

## 목차
1. [Single Source of Truth](#single-source-of-truth)
2. [환경별 설정](#환경별-설정)
3. [환경 변수 우선순위](#환경-변수-우선순위)
4. [설정 변경 방법](#설정-변경-방법)
5. [모범 사례](#모범-사례)

---

## Single Source of Truth

### 설정 중복 제거

**변경 전 (문제):**
```
설정이 3곳에 중복:
├── values.yaml
│   ├── routerAgent.env.redisHost: "redis"
│   └── sdbAgent.env.redisHost: "redis"
├── router-agent/app/config.py
│   └── redis_host = "redis"
└── sdb-agent/app/main.py
    └── REDIS_HOST = "redis"
```

**변경 후 (해결):**
```
values.yaml만 관리:
└── global.redis
    ├── host: "redis"
    ├── port: 6379
    ├── db: 0
    └── password: ""
```

### 현재 구조

#### 1. values.yaml - 유일한 설정 소스

```yaml
# helm/multi-agent-system/values.yaml
global:
  environment: local
  namespace: agent-system

  # Redis 공통 설정 (모든 Agent가 공유)
  redis:
    host: "redis"
    port: 6379
    db: 0
    password: ""  # 비어있으면 None
```

#### 2. Deployment 템플릿 - global.redis 참조

```yaml
# templates/router-agent/deployment.yaml
env:
  - name: REDIS_HOST
    value: {{ .Values.global.redis.host | quote }}
  - name: REDIS_PORT
    value: {{ .Values.global.redis.port | quote }}
  - name: REDIS_DB
    value: {{ .Values.global.redis.db | quote }}
  {{- if .Values.global.redis.password }}
  - name: REDIS_PASSWORD
    value: {{ .Values.global.redis.password | quote }}
  {{- end }}
```

```yaml
# templates/sdb-agent/deployment.yaml
env:
  - name: REDIS_HOST
    value: {{ .Values.global.redis.host | quote }}
  - name: REDIS_PORT
    value: {{ .Values.global.redis.port | quote }}
  - name: REDIS_DB
    value: {{ .Values.global.redis.db | quote }}
  {{- if .Values.global.redis.password }}
  - name: REDIS_PASSWORD
    value: {{ .Values.global.redis.password | quote }}
  {{- end }}
```

#### 3. 코드 - 기본값 최소화

**router-agent/app/config.py:**
```python
class Settings(BaseSettings):
    # Redis 설정 (Kubernetes: 환경 변수로 주입, 로컬: .env 또는 기본값)
    redis_host: str = "localhost"  # 로컬 개발 환경 기본값
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None

    class Config:
        env_file = ".env"
```

**sdb-agent/app/main.py:**
```python
# Redis 설정 (Kubernetes: 환경 변수로 주입, 로컬: .env 또는 기본값)
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')  # 로컬 개발 환경 기본값
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
REDIS_DB = int(os.getenv('REDIS_DB', '0'))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)
```

---

## 환경별 설정

### Kubernetes 환경

**설정 흐름:**
```
values.yaml
    ↓
Helm 템플릿 렌더링
    ↓
환경 변수로 Pod에 주입
    ↓
REDIS_HOST=redis
REDIS_PORT=6379
```

**설정 파일:**
```yaml
# helm/multi-agent-system/values.yaml
global:
  redis:
    host: "redis"       # Kubernetes Service 이름
    port: 6379
    db: 0
```

**확인 방법:**
```bash
# 환경 변수 확인
kubectl get pod -n agent-system -l app=router-agent -o yaml | grep -A 3 "REDIS_HOST"

# 출력:
# - name: REDIS_HOST
#   value: "redis"
```

---

### 로컬 개발 환경

**설정 흐름:**
```
.env 파일
    ↓
os.getenv()
    ↓
REDIS_HOST=localhost
```

**설정 파일:**
```bash
# .env (프로젝트 루트)
# Redis 설정 (로컬 개발용)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
```

**사용 방법:**
```bash
# 로컬 Redis 실행
docker run -d -p 6379:6379 redis:7.2-alpine

# 또는 시스템 Redis 사용
brew install redis  # macOS
apt-get install redis  # Ubuntu
redis-server

# Python 애플리케이션 실행
cd router-agent
python -m uvicorn app.main:app --host 0.0.0.0 --port 5000
```

---

### Docker Compose 환경

**설정 흐름:**
```
docker-compose.yml
    ↓
environment 또는 env_file
    ↓
REDIS_HOST=redis (서비스 이름)
```

**예시:**
```yaml
# docker-compose.yml
version: '3.8'

services:
  redis:
    image: redis:7.2-alpine
    ports:
      - "6379:6379"

  router-agent:
    build: ./router-agent
    environment:
      REDIS_HOST: redis      # Docker Compose 서비스 이름
      REDIS_PORT: 6379
      REDIS_DB: 0
    depends_on:
      - redis
```

---

## 환경 변수 우선순위

### 우선순위 순서

```
1순위: 직접 설정한 환경 변수
         ↓ (없으면)
2순위: Kubernetes가 주입한 환경 변수 (Deployment의 env)
         ↓ (없으면)
3순위: .env 파일 (Pydantic이 자동 로드)
         ↓ (없으면)
4순위: 코드의 기본값
```

### Kubernetes 배포 시

```python
# Pod 내부
# 환경 변수: REDIS_HOST="redis" (Kubernetes가 주입)

settings = Settings()
print(settings.redis_host)
# → "redis" ✅
# → 코드 기본값 "localhost" 무시됨
```

### 로컬 개발 시 (.env 있음)

```python
# .env 파일: REDIS_HOST=localhost

settings = Settings()
print(settings.redis_host)
# → "localhost" ✅
# → .env 파일에서 로드
```

### 로컬 개발 시 (.env 없음)

```python
# .env 파일 없음

settings = Settings()
print(settings.redis_host)
# → "localhost" ✅
# → 코드 기본값 사용
```

---

## 설정 변경 방법

### 시나리오 1: Redis 호스트 변경

**예시:** Redis를 외부 서비스로 변경

**변경 전:**
```yaml
# values.yaml
global:
  redis:
    host: "redis"
```

**변경 후:**
```yaml
# values.yaml
global:
  redis:
    host: "my-external-redis.example.com"
    port: 6380
    password: "my-secure-password"
```

**적용:**
```bash
# Helm upgrade
helm upgrade multi-agent-system ./helm/multi-agent-system -n agent-system

# Pod 재시작 대기
kubectl rollout status deployment/router-agent -n agent-system

# 확인
kubectl logs -n agent-system -l app=router-agent --tail=10 | grep -i redis
# 출력: Redis 연결 성공: my-external-redis.example.com:6380
```

---

### 시나리오 2: 환경별 설정 분리

**구조:**
```
helm/multi-agent-system/
├── values.yaml              # 기본 설정
├── values-dev.yaml          # 개발 환경
├── values-staging.yaml      # 스테이징 환경
└── values-production.yaml   # 프로덕션 환경
```

**values-dev.yaml:**
```yaml
# 개발 환경 오버라이드
global:
  environment: dev
  redis:
    host: "redis"           # 로컬 Redis
    password: ""            # 비밀번호 없음
```

**values-production.yaml:**
```yaml
# 프로덕션 환경 오버라이드
global:
  environment: production
  redis:
    host: "redis-ha.redis-system.svc.cluster.local"
    password: "CHANGE_ME"   # Secret으로 관리 권장

# 리소스 증가
routerAgent:
  replicaCount: 10
  resources:
    requests:
      memory: "512Mi"
      cpu: "500m"
```

**사용:**
```bash
# 개발 환경
helm upgrade multi-agent-system ./helm/multi-agent-system \
  -n agent-system \
  -f helm/multi-agent-system/values-dev.yaml

# 프로덕션 환경
helm upgrade multi-agent-system ./helm/multi-agent-system \
  -n agent-system \
  -f helm/multi-agent-system/values-production.yaml
```

---

### 시나리오 3: 비밀번호 Secret으로 관리

**Secret 생성:**
```bash
# Redis 비밀번호를 Secret으로 생성
kubectl create secret generic redis-password \
  --from-literal=password='my-secure-password' \
  -n agent-system
```

**Deployment 템플릿 수정:**
```yaml
# templates/router-agent/deployment.yaml
env:
  - name: REDIS_HOST
    value: {{ .Values.global.redis.host | quote }}
  - name: REDIS_PORT
    value: {{ .Values.global.redis.port | quote }}
  - name: REDIS_PASSWORD
    valueFrom:
      secretKeyRef:
        name: redis-password
        key: password
```

**values.yaml:**
```yaml
global:
  redis:
    host: "redis"
    port: 6379
    # password는 Secret에서 주입
```

---

## 모범 사례

### 1. values.yaml을 Single Source of Truth로 사용

**✅ 권장:**
```yaml
# values.yaml
global:
  redis:
    host: "redis"
    port: 6379
```

**❌ 비권장:**
```python
# 코드에 하드코딩
redis_host = "redis"  # ← 변경 어려움
```

---

### 2. 환경별 values 파일 분리

**✅ 권장:**
```
values.yaml           # 기본값
values-dev.yaml       # 개발 환경
values-prod.yaml      # 프로덕션 환경
```

**❌ 비권장:**
```yaml
# values.yaml에 모든 환경 설정
redis:
  dev:
    host: "redis-dev"
  prod:
    host: "redis-prod"
```

---

### 3. 민감 정보는 Secret 사용

**✅ 권장:**
```yaml
env:
  - name: REDIS_PASSWORD
    valueFrom:
      secretKeyRef:
        name: redis-password
        key: password
```

**❌ 비권장:**
```yaml
env:
  - name: REDIS_PASSWORD
    value: "my-password"  # ← Git에 노출
```

---

### 4. 코드 기본값 최소화

**✅ 권장:**
```python
# 로컬 개발을 위한 최소 기본값만
redis_host: str = "localhost"  # 로컬 개발용
```

**❌ 비권장:**
```python
# 환경별 분기 로직
if env == "production":
    redis_host = "redis-prod"
elif env == "staging":
    redis_host = "redis-staging"
else:
    redis_host = "localhost"
```

---

### 5. .env 파일은 Git 제외

**.gitignore:**
```
# 환경 변수 파일
.env
.env.local

# 예시 파일은 추적
!.env.example
```

**.env.example:**
```bash
# Redis 설정
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# OpenAI API
OPENAI_API_KEY=your-api-key-here
```

---

## 설정 검증

### Kubernetes 배포 후 확인

```bash
# 1. 환경 변수 확인
kubectl describe pod -n agent-system -l app=router-agent | grep -A 5 "Environment:"

# 2. 로그에서 Redis 연결 확인
kubectl logs -n agent-system -l app=router-agent --tail=20 | grep -i redis

# 3. Redis 연결 테스트
kubectl exec -it $(kubectl get pod -n agent-system -l app=router-agent -o jsonpath='{.items[0].metadata.name}') \
  -n agent-system -- sh -c 'env | grep REDIS'
```

### 로컬 개발 환경 확인

```bash
# 1. .env 파일 확인
cat .env | grep REDIS

# 2. Python에서 확인
python3 -c "
from router-agent.app.config import get_settings
settings = get_settings()
print(f'Redis Host: {settings.redis_host}')
print(f'Redis Port: {settings.redis_port}')
"
```

---

## 문제 해결

### 설정이 반영되지 않음

```bash
# 1. values.yaml 확인
grep -A 5 "global:" helm/multi-agent-system/values.yaml

# 2. Helm upgrade 실행
helm upgrade multi-agent-system ./helm/multi-agent-system -n agent-system

# 3. Pod 재시작 확인
kubectl get pods -n agent-system

# AGE가 최근(예: 30s)이면 재시작됨
```

### 환경 변수가 Pod에 없음

```bash
# Deployment 확인
kubectl get deployment router-agent -n agent-system -o yaml | grep -A 10 "env:"

# Helm 템플릿 렌더링 확인
helm template multi-agent-system ./helm/multi-agent-system | grep -A 5 "REDIS_HOST"
```

---

## 참고 자료

- [Redis 연결 원리](./REDIS_CONNECTION.md)
- [트러블슈팅 가이드](./REDIS_TROUBLESHOOTING.md)
- [배포 워크플로우](./DEPLOYMENT_WORKFLOW.md)
