# 환경 변수 동작 흐름 가이드

Multi-Agent 시스템에서 환경 변수가 어떻게 로드되고 사용되는지에 대한 전체 흐름을 설명합니다.

## 목차
1. [개요](#개요)
2. [로컬 개발 환경 흐름](#1-로컬-개발-환경-흐름)
3. [Kubernetes 환경 흐름](#2-kubernetes-환경-흐름)
4. [환경 변수 우선순위](#환경-변수-우선순위)
5. [주요 설정 파일](#주요-설정-파일)
6. [테스트 방법](#테스트-방법)

---

## 개요

Multi-Agent 시스템은 **Pydantic Settings**를 사용하여 환경 변수를 관리합니다. 이를 통해:
- ✅ 로컬 개발 시 `.env` 파일에서 자동 로드
- ✅ Kubernetes 환경에서 Secret/ConfigMap에서 자동 주입
- ✅ 타입 안전성 및 검증 자동화
- ✅ 두 agent(router-agent, sdb-agent) 간 일관된 설정 관리

---

## 1. 로컬 개발 환경 흐름

### 📋 흐름도

```
┌─────────────────────────┐
│     .env 파일            │
│  (agent 디렉토리)         │
│                         │
│  OPENAI_API_KEY=sk-...  │
│  BITBUCKET_TOKEN=ATCTT..│
│  REDIS_HOST=localhost   │
│  DB_HOST=localhost      │
└────────────┬────────────┘
             │
             ↓
┌─────────────────────────┐
│   Pydantic Settings     │
│   config.py             │
│                         │
│  class Settings(        │
│    BaseSettings):       │
│    openai_api_key: str  │
│    redis_host: str      │
│    ...                  │
│                         │
│  Config:                │
│    env_file = ".env"    │
│    case_sensitive=False │
└────────────┬────────────┘
             │ 자동 로드 및 타입 변환
             ↓
┌─────────────────────────┐
│    Python 코드           │
│                         │
│  settings = get_settings│
│  cache_manager = Cache( │
│    host=settings.       │
│         redis_host      │
│  )                      │
└─────────────────────────┘
```

### 📝 예시: sdb-agent 로컬 실행

```bash
# 1. .env 파일 생성
cd sdb-agent
cat > .env << EOF
# OpenAI 설정
OPENAI_API_KEY=sk-proj-your-key-here
OPENAI_MODEL=gpt-4-turbo-preview

# Bitbucket 설정
BITBUCKET_URL=https://api.bitbucket.org
BITBUCKET_USERNAME=your-email@example.com
BITBUCKET_ACCESS_TOKEN=ATCTTyour-token-here
BITBUCKET_WORKSPACE=your-workspace
BITBUCKET_REPOSITORY=your-repo

# Redis (로컬)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# PostgreSQL (로컬)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=agent_system
DB_USER=agent_user
DB_PASSWORD=yourpassword

# 테스트 모드
TEST_MODE=true
FLASK_ENV=development
EOF

# 2. 가상 환경 활성화
source ../venv312/bin/activate

# 3. 의존성 설치
pip install -r requirements.txt

# 4. 실행 (자동으로 .env 로드됨)
python app/main.py
```

### 🔍 config.py 구조

**sdb-agent/app/config.py:**
```python
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """SDB Agent 설정"""

    # Bitbucket 설정
    bitbucket_url: str = "https://api.bitbucket.org"
    bitbucket_username: str = "api_user"
    bitbucket_access_token: Optional[str] = None
    bitbucket_repository: str = "genw_new"
    bitbucket_workspace: str = "mit_dev"

    # OpenAI 설정
    openai_api_key: str = ""
    openai_model: str = "gpt-4-turbo-preview"

    # 로깅 설정
    log_level: str = "INFO"

    # Redis 설정
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None

    # PostgreSQL 설정
    db_host: str = "postgresql"
    db_port: int = 5432
    db_name: str = "agent_system"
    db_user: str = "agent_user"
    db_password: str = ""

    # 테스트 모드 설정
    test_mode: bool = False
    flask_env: str = "production"

    # Flask 포트 설정
    port: int = 5000

    class Config:
        env_file = ".env"              # .env 파일 자동 로드
        case_sensitive = False         # 대소문자 무시 (REDIS_HOST → redis_host)
        extra = "ignore"               # 정의되지 않은 필드 무시

def get_settings() -> Settings:
    """설정 인스턴스 반환"""
    return Settings()
```

### 🎯 주요 특징

1. **자동 타입 변환**
   ```python
   # .env: REDIS_PORT=6379 (문자열)
   # config.py: redis_port: int = 6379
   # 결과: 자동으로 int로 변환됨
   ```

2. **대소문자 무시**
   ```python
   # case_sensitive = False 덕분에:
   # REDIS_HOST → redis_host ✅
   # Redis_Host → redis_host ✅
   # redis_host → redis_host ✅
   ```

3. **기본값 제공**
   ```python
   # .env에 없으면 기본값 사용
   redis_host: str = "localhost"  # 기본값
   ```

---

## 2. Kubernetes 환경 흐름

### 📋 전체 흐름도

```
┌──────────────────┐
│   .env 파일       │
│ (프로젝트 root)   │
│                  │
│ OPENAI_API_KEY=..│
│ BITBUCKET_TOKEN=.│
└────────┬─────────┘
         │
         │ source .env
         ↓
┌─────────────────────────────────┐
│ create-secrets-from-env.sh      │
│                                 │
│ kubectl create secret \         │
│   --from-literal=openai-api-key │
│   --from-literal=bitbucket-...  │
└────────┬────────────────────────┘
         │
         ↓
┌────────────────────┐      ┌──────────────┐
│ Kubernetes Secret  │      │  ConfigMap   │
│  agent-secrets     │      │agent-config  │
│                    │      │              │
│ - openai-api-key   │      │ - OPENAI_MODEL│
│ - bitbucket-token  │      │ - LOG_LEVEL  │
│ - bitbucket-user   │      │ - BITBUCKET_*│
└────────┬───────────┘      └──────┬───────┘
         │                         │
         └──────────┬──────────────┘
                    │
                    ↓
         ┌──────────────────────┐
         │  deployment.yaml     │
         │                      │
         │  env:                │
         │  - name: OPENAI_KEY  │
         │    valueFrom:        │
         │      secretKeyRef:   │
         │        key: openai...│
         │  - name: LOG_LEVEL   │
         │    valueFrom:        │
         │      configMapKeyRef:│
         └──────────┬───────────┘
                    │
                    │ Pod 생성 시
                    ↓
         ┌──────────────────────┐
         │   Pod 환경 변수       │
         │                      │
         │ OPENAI_API_KEY=sk-...│
         │ REDIS_HOST=redis     │
         │ DB_HOST=postgresql   │
         │ LOG_LEVEL=INFO       │
         └──────────┬───────────┘
                    │
                    │ OS 환경 변수
                    ↓
         ┌──────────────────────┐
         │  Pydantic Settings   │
         │    config.py         │
         │                      │
         │  os.getenv() 또는    │
         │  자동 매핑           │
         └──────────┬───────────┘
                    │
                    ↓
         ┌──────────────────────┐
         │    Python 코드        │
         │                      │
         │  settings = get_...  │
         │  cache = CacheManager│
         │    (host=settings.   │
         │     redis_host)      │
         └──────────────────────┘
```

### 🔐 Secret 생성

**1. 프로젝트 루트에 .env 파일 생성:**
```bash
# .env (프로젝트 root)
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx
BITBUCKET_ACCESS_TOKEN=ATCTTxxxxxxxxx
BITBUCKET_USERNAME=hjm0830@midasit.com
BITBUCKET_WORKSPACE=mit_dev
BITBUCKET_REPOSITORY=genw_new
BITBUCKET_URL=https://api.bitbucket.org
```

**2. Secret 생성 스크립트 실행:**
```bash
./scripts/create-secrets-from-env.sh
```

**스크립트 내부 동작 (create-secrets-from-env.sh):**
```bash
#!/bin/bash

# .env 파일 로드
source .env

# 필수 환경 변수 확인
REQUIRED_VARS=(
    "OPENAI_API_KEY"
    "BITBUCKET_ACCESS_TOKEN"
    "BITBUCKET_USERNAME"
    "BITBUCKET_WORKSPACE"
    "BITBUCKET_REPOSITORY"
    "BITBUCKET_URL"
)

# Secret 생성
kubectl create secret generic agent-secrets \
  --from-literal=openai-api-key="$OPENAI_API_KEY" \
  --from-literal=bitbucket-access-token="$BITBUCKET_ACCESS_TOKEN" \
  --from-literal=bitbucket-username="$BITBUCKET_USERNAME" \
  -n agent-system
```

### 📦 ConfigMap 정의

**helm/multi-agent-system/templates/configmap.yaml:**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: agent-config
  namespace: agent-system
data:
  BITBUCKET_URL: "https://api.bitbucket.org"
  OPENAI_MODEL: "gpt-4-turbo-preview"
  LOG_LEVEL: "INFO"
  BITBUCKET_WORKSPACE: "mit_dev"
  BITBUCKET_REPOSITORY: "genw_new"
```

### 🚀 Deployment에서 환경변수 주입

**helm/multi-agent-system/templates/sdb-agent/deployment.yaml:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sdb-agent
spec:
  template:
    spec:
      containers:
      - name: sdb-agent
        image: sdb-agent:1.0.0
        env:
        # Secret에서 가져오기
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: agent-secrets
              key: openai-api-key

        - name: BITBUCKET_ACCESS_TOKEN
          valueFrom:
            secretKeyRef:
              name: agent-secrets
              key: bitbucket-access-token

        - name: BITBUCKET_USERNAME
          valueFrom:
            secretKeyRef:
              name: agent-secrets
              key: bitbucket-username

        # ConfigMap에서 가져오기
        - name: BITBUCKET_URL
          valueFrom:
            configMapKeyRef:
              name: agent-config
              key: BITBUCKET_URL

        - name: OPENAI_MODEL
          valueFrom:
            configMapKeyRef:
              name: agent-config
              key: OPENAI_MODEL

        - name: LOG_LEVEL
          valueFrom:
            configMapKeyRef:
              name: agent-config
              key: LOG_LEVEL

        # values.yaml에서 직접 주입
        - name: REDIS_HOST
          value: "redis"

        - name: REDIS_PORT
          value: "6379"

        - name: DB_HOST
          value: "postgresql"

        - name: DB_PORT
          value: "5432"

        # PostgreSQL 비밀번호는 별도 Secret
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgresql-secret
              key: POSTGRES_PASSWORD
```

### 📊 환경변수 출처 매핑표

| 환경 변수 | config.py 필드 | 출처 | 민감도 |
|----------|--------------|------|-------|
| OPENAI_API_KEY | openai_api_key | Secret: agent-secrets | 🔒 높음 |
| BITBUCKET_ACCESS_TOKEN | bitbucket_access_token | Secret: agent-secrets | 🔒 높음 |
| BITBUCKET_USERNAME | bitbucket_username | Secret: agent-secrets | 🔒 중간 |
| DB_PASSWORD | db_password | Secret: postgresql-secret | 🔒 높음 |
| OPENAI_MODEL | openai_model | ConfigMap: agent-config | 🔓 낮음 |
| LOG_LEVEL | log_level | ConfigMap: agent-config | 🔓 낮음 |
| BITBUCKET_URL | bitbucket_url | ConfigMap: agent-config | 🔓 낮음 |
| BITBUCKET_WORKSPACE | bitbucket_workspace | ConfigMap: agent-config | 🔓 낮음 |
| BITBUCKET_REPOSITORY | bitbucket_repository | ConfigMap: agent-config | 🔓 낮음 |
| REDIS_HOST | redis_host | values.yaml | 🔓 낮음 |
| REDIS_PORT | redis_port | values.yaml | 🔓 낮음 |
| REDIS_DB | redis_db | values.yaml | 🔓 낮음 |
| DB_HOST | db_host | values.yaml | 🔓 낮음 |
| DB_PORT | db_port | values.yaml | 🔓 낮음 |
| DB_NAME | db_name | values.yaml | 🔓 낮음 |
| DB_USER | db_user | values.yaml | 🔓 낮음 |
| TEST_MODE | test_mode | values.yaml | 🔓 낮음 |

---

## 환경 변수 우선순위

Pydantic Settings는 다음 순서로 값을 찾습니다:

```
1. OS 환경 변수 (최우선) ⭐
   - Kubernetes에서 주입된 환경 변수
   - export로 설정한 환경 변수
   ↓
2. .env 파일
   - 로컬 개발 환경에서 사용
   ↓
3. config.py의 기본값 (최후)
   - 위에서 찾지 못하면 기본값 사용
```

### 예시

```python
# config.py
class Settings(BaseSettings):
    redis_host: str = "localhost"  # 3. 기본값

    class Config:
        env_file = ".env"  # 2. .env 파일
```

```bash
# .env 파일
REDIS_HOST=192.168.1.100  # 2. .env 파일 값

# Kubernetes
env:
  - name: REDIS_HOST
    value: "redis"  # 1. OS 환경변수 (최우선!) ✅ 이 값이 사용됨
```

**결과:**
- Kubernetes 환경: `redis` (OS 환경변수)
- 로컬 (OS 환경변수 없음): `192.168.1.100` (.env 파일)
- 로컬 (.env도 없음): `localhost` (기본값)

---

## 주요 설정 파일

### 1. config.py (각 agent)

**위치:**
- `router-agent/app/config.py`
- `sdb-agent/app/config.py`

**역할:** 환경 변수 정의 및 타입 검증

### 2. deployment.yaml (각 agent)

**위치:**
- `helm/multi-agent-system/templates/router-agent/deployment.yaml`
- `helm/multi-agent-system/templates/sdb-agent/deployment.yaml`

**역할:** Pod에 환경 변수 주입

### 3. configmap.yaml

**위치:** `helm/multi-agent-system/templates/configmap.yaml`

**역할:** 비밀이 아닌 공통 설정 관리

### 4. values.yaml

**위치:** `helm/multi-agent-system/values.yaml`

**역할:** Helm Chart 설정 값 정의

### 5. create-secrets-from-env.sh

**위치:** `scripts/create-secrets-from-env.sh`

**역할:** .env 파일에서 Kubernetes Secret 생성

---

## 테스트 방법

### 로컬 환경 테스트

```bash
# 1. .env 파일 생성
cd sdb-agent
cat > .env << EOF
OPENAI_API_KEY=sk-test-key
REDIS_HOST=localhost
DB_HOST=localhost
EOF

# 2. 가상환경 활성화
source ../venv312/bin/activate

# 3. 의존성 설치
pip install -r requirements.txt

# 4. 실행
python app/main.py

# 5. 로그에서 설정값 확인
# Expected output:
# INFO - Redis 연결: localhost:6379
# INFO - DB 연결: localhost:5432
```

### Kubernetes 환경 테스트

```bash
# 1. .env 파일 생성 (프로젝트 root)
cat > .env << EOF
OPENAI_API_KEY=sk-proj-real-key
BITBUCKET_ACCESS_TOKEN=ATCTTreal-token
BITBUCKET_USERNAME=your-email@example.com
BITBUCKET_WORKSPACE=your-workspace
BITBUCKET_REPOSITORY=your-repo
BITBUCKET_URL=https://api.bitbucket.org
EOF

# 2. Secret 생성
./scripts/create-secrets-from-env.sh

# 3. Secret 확인
kubectl get secret agent-secrets -n agent-system -o yaml

# 4. Helm 배포
helm install multi-agent-system ./helm/multi-agent-system -n agent-system

# 5. Pod의 환경변수 확인
kubectl exec -n agent-system deployment/sdb-agent -- env | grep -E "OPENAI|BITBUCKET|REDIS|DB_"

# Expected output:
# OPENAI_API_KEY=sk-proj-real-key
# BITBUCKET_ACCESS_TOKEN=ATCTTreal-token
# BITBUCKET_USERNAME=your-email@example.com
# REDIS_HOST=redis
# DB_HOST=postgresql

# 6. Pod 로그 확인
kubectl logs -n agent-system -l app=sdb-agent --tail=50

# Expected output:
# INFO - Redis 연결: redis:6379
# INFO - DB 연결: postgresql:5432
# INFO - Bitbucket API 연결 성공!
```

### 환경변수 값 검증

```bash
# Pod 내부에서 직접 확인
kubectl exec -it -n agent-system deployment/sdb-agent -- /bin/sh

# 컨테이너 안에서:
env | grep OPENAI
env | grep REDIS
env | grep DB_

# Python에서 직접 확인
python3 << EOF
from app.config import get_settings
settings = get_settings()
print(f"OpenAI Key: {settings.openai_api_key[:10]}...")
print(f"Redis Host: {settings.redis_host}")
print(f"DB Host: {settings.db_host}")
EOF
```

---

## 문제 해결

### 1. 환경변수가 로드되지 않음

**증상:**
```
KeyError: 'OPENAI_API_KEY'
```

**해결:**
1. Secret이 생성되었는지 확인
   ```bash
   kubectl get secret agent-secrets -n agent-system
   ```

2. deployment.yaml에 환경변수 주입 확인
   ```bash
   kubectl get deployment sdb-agent -n agent-system -o yaml | grep -A 10 "env:"
   ```

3. Pod의 환경변수 확인
   ```bash
   kubectl exec -n agent-system deployment/sdb-agent -- env
   ```

### 2. .env 파일이 로드되지 않음 (로컬)

**증상:**
```python
# 기본값이 사용됨
redis_host = "localhost"  # .env의 값이 아닌 기본값
```

**해결:**
1. .env 파일 위치 확인
   ```bash
   ls -la .env
   # agent 디렉토리에 있어야 함 (sdb-agent/.env)
   ```

2. config.py의 env_file 설정 확인
   ```python
   class Config:
       env_file = ".env"  # ✅ 있어야 함
   ```

3. pydantic-settings 설치 확인
   ```bash
   pip show pydantic-settings
   ```

### 3. 대소문자 매핑 문제

**증상:**
```python
# OPENAI_API_KEY가 openai_api_key로 매핑되지 않음
```

**해결:**
```python
class Config:
    case_sensitive = False  # ✅ 이 설정 확인
```

---

## 관련 문서

- [Kubernetes Secret 자동화](../kubernetes/KUBERNETES_SECRET_AUTOMATION.md)
- [Redis 설정 관리](../redis/CONFIGURATION_MANAGEMENT.md)
- [배포 워크플로우](../redis/DEPLOYMENT_WORKFLOW.md)
- [PostgreSQL 통합 가이드](../../sdb-agent/doc/POSTGRESQL_INTEGRATION_GUIDE.md)

---

## 요약

### ✅ 핵심 포인트

1. **Pydantic Settings 사용**
   - 로컬: .env 파일 자동 로드
   - Kubernetes: OS 환경변수 자동 매핑

2. **환경 변수 우선순위**
   - OS 환경변수 > .env 파일 > 기본값

3. **보안**
   - 민감한 정보: Kubernetes Secret
   - 일반 설정: ConfigMap
   - 코드에는 기본값만

4. **일관성**
   - router-agent와 sdb-agent 동일한 구조
   - 타입 안전성 보장

5. **유지보수성**
   - 한 곳에서 관리 (values.yaml, Secret, ConfigMap)
   - 환경별 쉬운 설정 변경
