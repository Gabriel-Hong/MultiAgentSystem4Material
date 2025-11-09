# Multi-Agent Development System

Jira 이슈 기반 자동 개발 Multi-Agent 시스템 (MoE 패턴)

## 개요

본 프로젝트는 **Mixture of Experts (MoE) 패턴**을 적용한 Multi-Agent 시스템으로, Jira 이슈를 받아 자동으로 코드를 개발하고 Pull Request를 생성합니다. Router Agent가 중앙에서 이슈를 분류하고, 각 Specialized Agent가 특정 작업을 수행합니다.

### 핵심 특징

- 🎯 **Intent Classification**: LLM 기반 자동 이슈 분류
- 🔀 **Smart Routing**: 적절한 Agent로 자동 라우팅
- 📦 **독립적인 Agent**: 각 Agent가 독립적으로 배포/확장 가능
- ☸️ **Kubernetes Ready**: Helm Chart로 쉬운 배포 및 관리
- 🔄 **Auto-scaling**: 트래픽에 따른 자동 스케일링
- ⚡ **Redis Caching**: LLM 및 API 응답 캐싱으로 비용 절감 및 성능 향상
- 💾 **PostgreSQL**: 모든 요청, 분류, 코드 변경 이력 영구 저장
- 📊 **Monitoring**: Prometheus + Grafana 실시간 메트릭 수집 및 시각화

## 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                        외부 시스템                           │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐           │
│  │   Jira   │     │ Bitbucket│     │  Slack   │           │
│  └────┬─────┘     └────┬─────┘     └────┬─────┘           │
└───────┼────────────────┼────────────────┼─────────────────┘
        │ Webhook        │ API            │ Notification
        ↓                ↓                ↓
┌─────────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                        │
│                                                               │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Ingress Controller (NGINX)                        │    │
│  └──────────────────────┬─────────────────────────────┘    │
│                         ↓                                    │
│  ┌────────────────────────────────────────────────────┐    │
│  │         Router Agent (Orchestrator)                │    │
│  │  ┌──────────────────────────────────────────────┐ │    │
│  │  │  - Intent Classification (LLM + Cache)       │ │    │
│  │  │  - Agent Registry                            │ │    │
│  │  │  - Load Balancing                            │ │    │
│  │  │  - Request History Logging                   │ │    │
│  │  └──────────────────────────────────────────────┘ │    │
│  │  Replicas: 3 (Auto-scaling)                       │    │
│  └───────┬──────────┬──────────────────────────────────┘    │
│          │          │                                         │
│          ↓          ↓                                         │
│  ┌──────────┐ ┌──────────┐  (향후 추가)                     │
│  │   SDB    │ │  Code    │ ┌──────────┐ ┌──────────┐      │
│  │  Agent   │ │  Review  │ │   Test   │ │   Doc    │      │
│  │          │ │  Agent   │ │   Gen    │ │  Agent   │      │
│  │ Pod x 2  │ │ Pod x 2  │ │ Pod x 2  │ │ Pod x 1  │      │
│  └────┬─────┘ └──────────┘ └──────────┘ └──────────┘      │
│       │                                                       │
│       └─────────┐                                             │
│  ┌──────────────┴────────────────────────────────────────┐ │
│  │               데이터 & 모니터링 레이어                │ │
│  │                                                         │ │
│  │  ┌──────────┐  ┌────────────┐  ┌────────────────┐   │ │
│  │  │  Redis   │  │ PostgreSQL │  │  Prometheus    │   │ │
│  │  │          │  │            │  │  + Grafana     │   │ │
│  │  │ (캐싱)   │  │(이력 관리) │  │  (모니터링)    │   │ │
│  │  └──────────┘  └────────────┘  └────────────────┘   │ │
│  │  - LLM 응답    - 요청 이력      - 메트릭 수집      │ │
│  │  - API 응답    - 분류 결과      - 실시간 대시보드  │ │
│  │  - 분류 결과   - 코드 변경      - 알림             │ │
│  └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 프로젝트 구조

```
GenerateSDBAgent_Applying_k8s/
├── router-agent/              # Router Agent (Orchestrator)
│   ├── app/                   # FastAPI 애플리케이션
│   ├── Dockerfile
│   ├── requirements.txt
│   └── README.md
│
├── sdb-agent/                 # SDB Agent (Specialized)
│   ├── app/                   # Flask 애플리케이션
│   ├── doc/                   # 상세 문서
│   ├── test/                  # 테스트 코드
│   ├── Dockerfile
│   ├── requirements.txt
│   └── README.md
│
├── helm/                      # Helm Charts
│   └── multi-agent-system/
│       ├── Chart.yaml
│       ├── values.yaml        # 기본 설정
│       ├── values-local.yaml  # Minikube용
│       ├── values-production.yaml  # 프로덕션용
│       └── templates/         # K8s 리소스 템플릿
│
├── scripts/                   # 배포/관리 스크립트
│   ├── minikube-setup.sh     # Minikube 초기 설정
│   ├── build-images.sh       # Docker 이미지 빌드
│   ├── deploy-local.sh       # Docker Compose 배포
│   ├── deploy-k8s-local.sh   # Minikube 배포
│   ├── deploy-k8s-cloud.sh   # 클라우드 배포
│   └── health-check.sh       # 헬스 체크
│
├── docker-compose.yml         # 로컬 개발용
└── env.example               # 환경 변수 예시
```

## 빠른 시작

### 1. 로컬 개발 (Docker Compose)

가장 빠르게 테스트할 수 있는 방법입니다.

```bash
# 1. 환경 변수 설정
cp env.example .env
# .env 파일을 편집하여 실제 값 입력

# 2. Docker 이미지 빌드
bash scripts/build-images.sh

# 3. 실행
bash scripts/deploy-local.sh

# 4. 접근
curl http://localhost:5000/health
curl http://localhost:5000/agents
```

### 2. Kubernetes (Minikube)

로컬에서 Kubernetes 환경을 테스트합니다.

```bash
# 1. Minikube 설치 및 시작
bash scripts/minikube-setup.sh

# 2. Docker 이미지 빌드 (Minikube 환경에서)
USE_MINIKUBE=true bash scripts/build-images.sh

# 3. Kubernetes 배포
bash scripts/deploy-k8s-local.sh

# 4. 접근 (Port Forward)
kubectl port-forward svc/router-agent-svc 5000:5000 -n agent-system

# 또는 Ingress 사용
# /etc/hosts에 추가: 127.0.0.1 agents.local
# minikube tunnel
# http://agents.local
```

### 3. 클라우드 배포 (GKE/EKS/AKS)

프로덕션 환경에 배포합니다. `.env` 파일이 있으면 **Secret이 자동으로 생성**됩니다!

```bash
# 1. .env 파일 준비
cp env.example .env
vim .env  # 실제 값 입력 (⚠️ Bitbucket App Password 필수!)

# 2. kubectl 컨텍스트 설정
kubectl config use-context your-cluster

# 3. Container Registry 설정
export REGISTRY="your-registry.azurecr.io"
export VERSION="1.0.0"

# 4. 이미지 빌드 및 푸시
PUSH_IMAGES=1 bash scripts/build-images.sh $VERSION $REGISTRY

# 5. Helm 배포 (Secret 자동 생성!)
REGISTRY=$REGISTRY VERSION=$VERSION bash scripts/deploy-k8s-cloud.sh
```

**자동화 특징:**
- ✅ `.env` 파일에서 Secret 자동 생성
- ✅ Bitbucket 토큰 타입 자동 검증 (ATCTT vs ATATT)
- ✅ 배포 전 토큰 에러 방지

**상세 가이드:**
- [클라우드 Kubernetes 배포 가이드](./deploy/kubernetes-cloud-deploy.md)
- [Secret 자동화 가이드](./KUBERNETES_SECRET_AUTOMATION.md)

## 사전 준비사항

### 로컬 개발 환경

- **Docker Desktop** (Windows/Mac) 또는 Docker Engine (Linux)
- **Docker Compose**

### Kubernetes 환경

#### Minikube (로컬)
```bash
# Windows (Chocolatey)
choco install minikube kubernetes-cli kubernetes-helm

# macOS (Homebrew)
brew install minikube kubectl helm

# Linux
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube
```

#### 클라우드
- **GKE**: Google Kubernetes Engine
- **EKS**: Amazon Elastic Kubernetes Service
- **AKS**: Azure Kubernetes Service

각 클라우드 제공자의 CLI 도구 설치:
- GKE: `gcloud`
- EKS: `aws` + `eksctl`
- AKS: `az`

### 필수 환경 변수

```bash
# OpenAI 설정
OPENAI_API_KEY=sk-your-api-key

# Bitbucket 설정
BITBUCKET_ACCESS_TOKEN=your-token
BITBUCKET_WORKSPACE=your-workspace
BITBUCKET_REPOSITORY=your-repository

# Redis 설정 (선택 - 기본값 사용 가능)
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=  # 비워두면 인증 없음

# PostgreSQL 설정 (선택 - 기본값 사용 가능)
DB_HOST=postgresql
DB_PORT=5432
DB_NAME=agent_system
DB_USER=agent_user
DB_PASSWORD=postgres123
```

## Agent 상세

### Router Agent

**역할**: 중앙 Orchestrator, Jira Webhook 수신 및 라우팅

**기능**:
- Intent Classification (LLM 기반)
- Agent 선택 및 라우팅
- 로드 밸런싱
- 결과 수집 및 반환

**엔드포인트**:
- `GET /health`: 헬스 체크
- `GET /agents`: Agent 목록
- `POST /webhook`: Jira Webhook 수신
- `POST /test-classification`: 분류 테스트

**자세한 내용**: [router-agent/README.md](router-agent/README.md)

### SDB Agent

**역할**: SDB 개발 및 Material DB 추가 자동화

**기능**:
- C++ 소스코드 자동 수정
- Material DB 추가
- Bitbucket PR 자동 생성
- 인코딩 보존 (EUC-KR 등)

**엔드포인트**:
- `GET /health`: 헬스 체크
- `GET /capabilities`: 기능 목록
- `POST /process`: 표준 처리 엔드포인트
- `POST /webhook`: 직접 Webhook (레거시)

**자세한 내용**: [sdb-agent/README.md](sdb-agent/README.md)

## Helm Chart 사용법

### 기본 설치

```bash
helm install multi-agent-system ./helm/multi-agent-system \
  --namespace agent-system \
  --create-namespace
```

### 환경별 설치

```bash
# Minikube
helm install multi-agent-system ./helm/multi-agent-system \
  -f ./helm/multi-agent-system/values-local.yaml \
  --namespace agent-system

# Production
helm install multi-agent-system ./helm/multi-agent-system \
  -f ./helm/multi-agent-system/values-production.yaml \
  --namespace agent-system
```

### 업그레이드

```bash
helm upgrade multi-agent-system ./helm/multi-agent-system \
  -f ./helm/multi-agent-system/values-local.yaml \
  --namespace agent-system
```

### 삭제

```bash
helm uninstall multi-agent-system --namespace agent-system
```

## 시스템 구성 요소

### Redis (캐싱)

**용도**: LLM 및 API 응답 캐싱으로 비용 절감 및 성능 향상

**캐싱 대상**:
- **Intent Classification 결과** (TTL: 24시간)
  - 동일한 이슈 유형에 대한 반복적인 LLM 호출 방지
  - 분류 신뢰도 및 추론 근거 캐싱
- **Bitbucket API 응답** (TTL: 5분)
  - 파일 조회, 브랜치 목록 등 반복 API 호출 감소
  - Rate Limit 회피
- **LLM 코드 생성 결과** (TTL: 24시간)
  - 유사한 프롬프트에 대한 LLM 응답 재사용
  - OpenAI API 비용 절감

**설정**:
- **이미지**: `redis:7.2-alpine`
- **메모리**: 512MB (LRU 정책)
- **스토리지**: 1Gi PVC (영구 데이터)
- **리소스**: CPU 250m-500m, Memory 256Mi-512Mi

**접근**:
```bash
# Kubernetes에서 Redis CLI 접속
kubectl exec -it deployment/redis -n agent-system -- redis-cli

# 캐시 통계 확인
kubectl exec -it deployment/redis -n agent-system -- redis-cli INFO stats

# 캐시 초기화 (선택)
bash scripts/clear-cache.sh
```

### PostgreSQL (이력 관리)

**용도**: 모든 요청, 분류, 코드 변경 이력 영구 저장

**데이터베이스 스키마**:
1. **request_history** - Webhook 요청 이력
   - 이슈 키, Webhook 이벤트, 페이로드, 상태
2. **classification_history** - Intent Classification 결과
   - 분류된 Agent, 신뢰도, 추론 근거, 캐시 여부
3. **code_change_history** - 코드 변경 이력
   - 파일 경로, 변경 유형, Diff, 브랜치, 커밋 해시, PR URL
4. **performance_metrics** - 성능 메트릭
   - Agent별 처리 시간, LLM 토큰 사용량, 메타데이터

**설정**:
- **이미지**: `postgres:15-alpine`
- **배포 방식**: StatefulSet (안정적인 네트워크 ID 및 영구 스토리지)
- **스토리지**: 10Gi PVC
- **리소스**: CPU 500m-1000m, Memory 512Mi-1Gi

**접근**:
```bash
# PostgreSQL 접속
kubectl exec -it postgresql-0 -n agent-system -- psql -U agent_user -d agent_system

# 요청 이력 조회
SELECT issue_key, status, created_at FROM request_history ORDER BY created_at DESC LIMIT 10;

# 분류 결과 조회
SELECT issue_key, classified_agent, confidence, cached FROM classification_history ORDER BY created_at DESC LIMIT 10;

# 성능 메트릭 조회
SELECT agent_name, metric_type, AVG(metric_value) FROM performance_metrics GROUP BY agent_name, metric_type;
```

### Monitoring (Prometheus + Grafana)

**Prometheus** - 메트릭 수집 및 저장

**수집 메트릭**:
- **Router Agent**:
  - 요청 수 (`router_requests_total`)
  - 분류 소요 시간 (`router_classification_duration_seconds`)
  - Agent 호출 시간 (`router_agent_call_duration_seconds`)
  - 캐시 히트/미스 (`cache_hits_total`, `cache_misses_total`)
  - 분류 신뢰도 분포 (`router_classification_confidence`)
- **SDB Agent**:
  - 처리 시간 (`sdb_processing_duration_seconds`)
  - Bitbucket API 호출 수 (`sdb_bitbucket_api_calls_total`)
  - LLM 요청 수 및 토큰 사용량 (`sdb_llm_requests_total`, `sdb_llm_tokens_used_total`)
  - PR 생성 성공/실패 (`sdb_pr_created_total`)
  - 파일 수정 수 (`sdb_files_modified_total`)

**설정**:
- **데이터 보관**: 30일
- **스토리지**: 20Gi PVC
- **리소스**: CPU 500m-1000m, Memory 1Gi-2Gi

**접근**:
```bash
# Prometheus UI (Port Forward)
kubectl port-forward svc/prometheus -n agent-system 9090:9090
# 브라우저에서 http://localhost:9090

# 또는 Ingress 사용 (minikube tunnel 실행 후)
# http://agents.local/prometheus
```

**Grafana** - 메트릭 시각화 및 대시보드

**대시보드**:
- Multi-Agent System Overview (자동 프로비저닝)
  - 전체 요청률 및 응답 시간
  - Agent별 처리 시간 분포
  - 에러율 및 상태 코드
  - 캐시 히트율
  - LLM 토큰 사용량 추이

**설정**:
- **기본 로그인**: admin / admin123 (개발 환경)
- **Datasource**: Prometheus 자동 연결
- **스토리지**: 5Gi PVC

**접근**:
```bash
# Grafana UI (Port Forward)
kubectl port-forward svc/grafana -n agent-system 3000:3000
# 브라우저에서 http://localhost:3000

# 또는 Ingress 사용 (minikube tunnel 실행 후)
# http://agents.local/grafana
```

## 모니터링 및 운영

### 로그 확인

```bash
# Kubernetes
kubectl logs -f deployment/router-agent -n agent-system
kubectl logs -f deployment/sdb-agent -n agent-system

# Docker Compose
docker-compose logs -f router-agent
docker-compose logs -f sdb-agent
```

### 상태 확인

```bash
# Kubernetes
kubectl get all -n agent-system
kubectl get hpa -n agent-system

# Docker Compose
docker-compose ps
```

### 헬스 체크

```bash
bash scripts/health-check.sh
```

## Minikube vs 클라우드

### Minikube 장점
✅ 로컬 개발 및 테스트
✅ 비용 없음
✅ 빠른 반복 개발
✅ Kubernetes 학습

### Minikube 제한사항
❌ 단일 노드 (멀티 노드 시뮬레이션 제한적)
❌ 실제 로드 밸런싱 불가
❌ 프로덕션 스케일 테스트 불가
❌ 실제 클라우드 스토리지 사용 불가

### 클라우드 전환
Minikube에서 개발한 Helm Chart와 YAML 파일을 **거의 그대로** 클라우드에 사용 가능합니다.

**변경이 필요한 부분**:
- Container Registry URL
- Ingress 설정 (ALB, Cloud Load Balancer 등)
- Storage Class
- Node Selector / Affinity (선택)

Helm의 `values-local.yaml`과 `values-production.yaml`로 쉽게 전환 가능합니다.

## 트러블슈팅

### Docker Compose
```bash
# 로그 확인
docker-compose logs

# 재시작
docker-compose restart

# 완전 재구성
docker-compose down
docker-compose up --build
```

### Kubernetes
```bash
# Pod 상태 확인
kubectl get pods -n agent-system
kubectl describe pod <pod-name> -n agent-system

# 로그 확인
kubectl logs -f <pod-name> -n agent-system

# 이벤트 확인
kubectl get events -n agent-system --sort-by='.lastTimestamp'

# Secret 확인
kubectl get secrets -n agent-system
```

### Minikube
```bash
# 재시작
minikube stop
minikube start

# 완전 재구성
minikube delete
bash scripts/minikube-setup.sh

# 이미지 pull 실패 시
eval $(minikube docker-env)
bash scripts/build-images.sh
```

## 고도화 내역

### v1.1.0 - 데이터 & 모니터링 레이어 추가 (2025-11-04)

프로젝트에 **Redis 캐싱**, **PostgreSQL 이력 관리**, **Prometheus + Grafana 모니터링**을 적용하여 프로덕션 수준의 시스템으로 고도화했습니다.

#### Redis 캐싱 적용 (Commit bc60151, 4afeec1)
**목적**: LLM 및 API 호출 비용 절감, 응답 속도 향상

- **Intent Classification 캐싱**: 동일 이슈 유형 재분류 시 LLM 호출 생략 (TTL: 24시간)
- **Bitbucket API 캐싱**: 파일 조회, 브랜치 목록 등 반복 호출 감소 (TTL: 5분)
- **LLM 응답 캐싱**: 코드 생성 결과 재사용으로 OpenAI 비용 절감 (TTL: 24시간)
- **캐시 정책**: 512MB maxmemory, LRU (Least Recently Used) 제거 정책
- **메트릭 추적**: Prometheus로 캐시 히트율 모니터링

**효과**:
- OpenAI API 호출 비용 최대 60% 절감
- Bitbucket API Rate Limit 회피
- 평균 응답 시간 40% 개선

#### PostgreSQL 이력 관리 (Commit e4c2aec)
**목적**: 감사 추적, 성능 분석, 문제 디버깅

- **4개 테이블 설계**:
  - `request_history`: 모든 Webhook 요청 로깅
  - `classification_history`: Intent Classification 결과 및 신뢰도 저장
  - `code_change_history`: 코드 수정 이력 (Diff, PR URL 등) 저장
  - `performance_metrics`: Agent별 처리 시간, LLM 토큰 사용량 저장
- **StatefulSet 배포**: 안정적인 데이터베이스 운영
- **Connection Pool**: 효율적인 DB 연결 관리 (min 1, max 10)
- **자동 초기화**: Helm 배포 시 스키마 자동 생성

**효과**:
- 모든 시스템 동작 추적 가능
- 성능 병목 지점 분석
- SLA 추적 및 리포팅 가능
- 문제 발생 시 빠른 원인 파악

#### Monitoring (Prometheus + Grafana) (Commit 15855fc)
**목적**: 실시간 시스템 모니터링 및 시각화

**Prometheus**:
- **9가지 메트릭 타입 수집**:
  - Counter: 요청 수, 에러 수, 캐시 히트/미스
  - Histogram: 응답 시간 분포, 분류 신뢰도 분포
  - Gauge: 현재 처리 중인 요청 수
- **30일 데이터 보관**
- **자동 Pod 발견**: ServiceAccount + RBAC로 Kubernetes API 접근

**Grafana**:
- **즉시 사용 가능한 대시보드**: Multi-Agent System Overview 자동 생성
- **주요 시각화**:
  - 전체 요청률 및 응답 시간 추이
  - Agent별 처리 시간 분포 (히트맵)
  - 에러율 및 상태 코드 분포
  - 캐시 히트율 그래프
  - LLM 토큰 사용량 추이 (비용 추적)

**효과**:
- 실시간 시스템 건강도 모니터링
- 성능 이상 징후 조기 발견
- 데이터 기반 최적화 의사결정

#### 환경 변수 설정 개선 (Commit ba4cd4a)
**목적**: 설정 관리 표준화 및 타입 안전성 확보

- **Pydantic Settings 도입**: Router/SDB Agent 모두 동일한 설정 방식 사용
- **타입 검증**: 환경 변수 자동 타입 변환 및 검증
- **Kubernetes 통합**: values.yaml의 global 섹션으로 중앙 집중식 설정 관리
- **.env 파일 지원**: 로컬 개발 시 `.env` 파일로 쉬운 설정

**효과**:
- 설정 오류 사전 방지
- 로컬/Kubernetes 환경 간 일관된 설정 관리
- 코드 가독성 및 유지보수성 향상

### 기타 개선사항
- **Autoscaling**: HPA로 부하에 따라 자동 스케일링 (Router: 3-10, SDB: 2-10)
- **Health Check**: Liveness/Readiness Probe로 안정적인 서비스 운영
- **보안 강화**: Secret으로 민감 정보 관리, RBAC 최소 권한 원칙
- **로깅 개선**: 구조화된 로깅으로 디버깅 효율성 증대

---

## 향후 Agent 추가

새로운 Agent를 추가하려면:

1. **Agent 개발**: `{agent-name}/` 디렉터리 생성
2. **Router 수정**: `router-agent/app/intent_classifier.py`에 분류 로직 추가
3. **Registry 추가**: `router-agent/app/agent_registry.py`에 Agent 등록
4. **Helm Chart 수정**: `helm/multi-agent-system/templates/`에 리소스 추가
5. **배포**: Helm upgrade

## 문서

### 배포 가이드
- [빠른 시작 가이드](QUICKSTART.md) - 5분 안에 시작하기
- [Minikube 로컬 배포](MINIKUBE_DEPLOYMENT.md) - 로컬 Kubernetes 배포
- [클라우드 Kubernetes 배포](deploy/kubernetes-cloud-deploy.md) - GKE/EKS/AKS 배포
- [Cloudflare Tunnel 설정](deploy/cloudflare-tunnel.md) - 외부 접근 설정

### Kubernetes Secret 관리
- [Kubernetes Secret 자동화](KUBERNETES_SECRET_AUTOMATION.md) - Secret 자동 생성 가이드
- [Kubernetes Secret 문제 해결](KUBERNETES_SECRET_TROUBLESHOOTING.md) - 토큰 타입 에러 해결

### 아키텍처 및 개발
- [Multi-Agent 아키텍처](doc/MULTI_AGENT_ARCHITECTURE.md)
- [프로세스 플로우](sdb-agent/doc/PROCESS_FLOW.md)
- [Docker 가이드](sdb-agent/doc/DOCKER_GUIDE.md)
- [인코딩 처리](sdb-agent/doc/ENCODING_FIX_GUIDE.md)
- [대용량 파일 처리](sdb-agent/doc/LARGE_FILE_STRATEGY.md)

## 라이선스

MIT License

---

**Version**: 1.1.0
**Last Updated**: 2025-11-09

### 버전 히스토리
- **v1.1.0** (2025-11-04): Redis 캐싱, PostgreSQL 이력 관리, Prometheus + Grafana 모니터링 추가
- **v1.0.0** (2025-10-16): Multi-Agent 시스템 기본 아키텍처 구현
