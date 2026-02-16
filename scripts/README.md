# Scripts 가이드

이 문서는 `scripts/` 폴더의 bash 스크립트들의 구조와 사용법을 설명합니다.

## 📊 스크립트 구조 개요

```
┌─────────────────────────────────────────────────────────────┐
│                     사용자 진입점 (Entry Points)                │
└─────────────────────────────────────────────────────────────┘

┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ minikube-setup  │  │  build-images   │  │  deploy-local   │
│      .sh        │  │      .sh        │  │      .sh        │
└─────────────────┘  └─────────────────┘  └─────────────────┘
        │                     │                     │
        │                     │                     │
        └─────────┬───────────┴─────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                    중간 레벨 스크립트                           │
└─────────────────────────────────────────────────────────────┘

        ┌────────────────────┬────────────────────┐
        ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│deploy-k8s-local │  │deploy-k8s-cloud │  │ start-tunnel    │
│      .sh        │  │      .sh        │  │      .sh        │
└─────────────────┘  └─────────────────┘  └─────────────────┘
        │                    │
        └──────────┬─────────┘
                   │
                   │ 호출 (source/call)
                   ▼
┌─────────────────────────────────────────────────────────────┐
│                  공통 유틸리티 스크립트                          │
└─────────────────────────────────────────────────────────────┘

    ┌──────────────────────┬──────────────────────┐
    ▼                      ▼                      ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│create-secrets│  │health-check  │  │ view-logs    │
│  -from-env   │  │    .sh       │  │    .sh       │
│    .sh       │  │              │  │              │
└──────────────┘  └──────────────┘  └──────────────┘
```

## 📁 스크립트 목록 및 설명

### 1️⃣ 독립 실행형 스크립트 (최상위)

#### `minikube-setup.sh`
**역할**: Minikube 클러스터 초기 설정

**기능**:
- Minikube 및 kubectl 설치 확인
- Minikube 클러스터 시작 (4 CPU, 8GB RAM)
- 필수 Addons 활성화 (ingress, metrics-server)
- Ingress Controller 준비 대기

**사용법**:
```bash
./scripts/minikube-setup.sh
```

**다음 단계**: `build-images.sh` 또는 `deploy-k8s-local.sh`

---

#### `build-images.sh`
**역할**: Docker 이미지 빌드 및 선택적으로 레지스트리에 푸시

**기능**:
- Router Agent 이미지 빌드
- SDB Agent 이미지 빌드
- Minikube Docker 환경 자동 감지
- 레지스트리 태깅 및 푸시 (옵션)

**사용법**:
```bash
# 기본 (latest 태그, Minikube 환경)
./scripts/build-images.sh

# 버전 지정
./scripts/build-images.sh v1.0.0

# 레지스트리에 푸시
PUSH_IMAGES=1 ./scripts/build-images.sh v1.0.0 myregistry.azurecr.io
```

**환경 변수**:
- `VERSION`: 이미지 태그 (기본값: latest)
- `REGISTRY`: Docker 레지스트리 URL (기본값: docker.io)
- `USE_MINIKUBE`: Minikube Docker 환경 사용 여부 (기본값: true)
- `PUSH_IMAGES`: 이미지 푸시 여부 (기본값: 없음)

**다음 단계**: `deploy-k8s-local.sh` 또는 `deploy-k8s-cloud.sh`

---

#### `deploy-local.sh`
**역할**: Docker Compose를 사용한 로컬 배포

**기능**:
- .env 파일 확인 및 생성 안내
- Docker Compose로 서비스 시작
- 헬스 체크 수행

**사용법**:
```bash
./scripts/deploy-local.sh
```

**전제 조건**:
- Docker 및 Docker Compose 설치
- `.env` 파일 준비 (env.example 참고)

**서비스 접근**:
- Router Agent: http://localhost:5000
- Health Check: http://localhost:5000/health

**중지**:
```bash
docker-compose down
```

---

### 2️⃣ Kubernetes 배포 스크립트 (중간 레벨)

#### `deploy-k8s-local.sh`
**역할**: Minikube Kubernetes 환경에 Helm을 사용하여 배포

**기능**:
- Helm 및 Minikube 상태 확인
- kubectl 컨텍스트 확인
- Secret 자동 생성 (`.env` 파일 있을 시)
- Helm Chart 배포 (values-local.yaml 사용)
- Port Forward 자동 설정 (옵션)
- 헬스 체크

**사용법**:
```bash
./scripts/deploy-k8s-local.sh
```

**전제 조건**:
- Minikube 실행 중 (`minikube-setup.sh` 실행)
- Docker 이미지 빌드 완료 (`build-images.sh` 실행)
- `.env` 파일 준비 (권장)

**호출 관계**:
- `create-secrets-from-env.sh --auto` (조건부 자동 호출)

**서비스 접근 방법**:
1. Port Forward: `kubectl port-forward svc/router-agent-svc 5000:5000 -n agent-system`
2. Minikube Service: `minikube service router-agent-svc -n agent-system`
3. Ingress: `minikube tunnel` 실행 후 http://agents.local

---

#### `deploy-k8s-cloud.sh`
**역할**: 프로덕션 Kubernetes 환경에 Helm을 사용하여 배포

**기능**:
- 프로덕션 배포 확인 프롬프트
- Secret 자동 생성 (`.env` 파일 있을 시)
- 이미지 레지스트리 준비 확인
- Helm Chart 배포 (values-production.yaml 사용)
- Ingress 및 TLS 설정 안내

**사용법**:
```bash
REGISTRY=myregistry.azurecr.io VERSION=v1.0.0 ./scripts/deploy-k8s-cloud.sh
```

**전제 조건**:
- 프로덕션 Kubernetes 클러스터 접근 가능
- Docker 이미지가 레지스트리에 푸시됨
- `.env` 파일 준비 (권장)

**환경 변수**:
- `REGISTRY`: Docker 레지스트리 URL (필수)
- `VERSION`: 이미지 버전 태그 (기본값: 1.0.0)

**호출 관계**:
- `create-secrets-from-env.sh --auto` (조건부 자동 호출)

---

### 3️⃣ 공통 유틸리티 스크립트 (하위 레벨)

#### `create-secrets-from-env.sh`
**역할**: `.env` 파일에서 Kubernetes Secret 생성

**기능**:
- .env 파일 로드 및 검증
- 필수 환경 변수 확인
- Bitbucket 토큰 타입 검증 (ATCTT vs ATATT)
- Kubernetes Secret 생성
- Secret 검증 및 확인

**사용법**:
```bash
# 대화형 모드
./scripts/create-secrets-from-env.sh

# 자동 모드 (프롬프트 생략)
./scripts/create-secrets-from-env.sh --auto
```

**필수 환경 변수**:
- `OPENAI_API_KEY`: OpenAI API 키
- `BITBUCKET_ACCESS_TOKEN`: Bitbucket App Password (ATCTT로 시작)
- `BITBUCKET_USERNAME`: Bitbucket 사용자 이메일
- `BITBUCKET_WORKSPACE`: Bitbucket 워크스페이스
- `BITBUCKET_REPOSITORY`: Bitbucket 저장소
- `BITBUCKET_URL`: Bitbucket API URL

**선택적 환경 변수**:
- `JIRA_URL`: Jira 인스턴스 URL
- `JIRA_EMAIL`: Jira 사용자 이메일
- `JIRA_API_TOKEN`: Jira API 토큰

**호출됨 (by)**:
- `deploy-k8s-local.sh` (line 65)
- `deploy-k8s-cloud.sh` (line 60)

**주의사항**:
⚠️ **BITBUCKET_ACCESS_TOKEN은 반드시 Bitbucket App Password(ATCTT)를 사용하세요!**
- Jira API Token(ATATT)은 Bitbucket API에서 작동하지 않습니다.

---

#### `health-check.sh`
**역할**: Multi-Agent 시스템의 헬스 체크

**기능**:
- 실행 환경 자동 감지 (Docker Compose / Kubernetes)
- Pod/컨테이너 상태 확인
- Router Agent 헬스 체크
- SDB Agent 헬스 체크
- HPA 상태 확인 (Kubernetes)

**사용법**:
```bash
./scripts/health-check.sh
```

**출력 예시**:
```
환경: Kubernetes
=========================================
Kubernetes Pods 상태
=========================================
NAME                           READY   STATUS    RESTARTS   AGE
router-agent-xxx               1/1     Running   0          5m
sdb-agent-xxx                  1/1     Running   0          5m
```

---

#### `view-logs.sh`
**역할**: Agent 로그 확인 (대화형)

**기능**:
- 실행 환경 자동 감지
- 대화형 Agent 선택 메뉴
- 실시간 로그 스트리밍
- 최근 로그 확인

**사용법**:
```bash
./scripts/view-logs.sh
```

**옵션**:
1. Router Agent 로그
2. SDB Agent 로그
3. 모든 Agent 로그 (실시간)
4. 최근 로그만 (100줄)

---

#### `start-tunnel.sh`
**역할**: Cloudflare Tunnel 시작

**기능**:
- Quick Tunnel (임시 URL) 시작
- Named Tunnel (고정 URL) 시작
- 터널 URL 자동 추출

**사용법**:
```bash
./scripts/start-tunnel.sh
```

**옵션**:
1. Quick Tunnel: 즉시 시작 (임시 URL)
2. Named Tunnel: 설정 필요 (CLOUDFLARE_TUNNEL_TOKEN)
3. 종료

**관련 파일**: `docker-compose.cloudflare.yml`

---

## 🎯 실행 시퀀스

### 시나리오 1: Minikube 로컬 개발

```bash
# 1. Minikube 클러스터 설정
./scripts/minikube-setup.sh

# 2. Docker 이미지 빌드
./scripts/build-images.sh

# 3. Kubernetes 배포
./scripts/deploy-k8s-local.sh

# 4. 헬스 체크
./scripts/health-check.sh

# 5. 로그 확인
./scripts/view-logs.sh
```

### 시나리오 2: Docker Compose 로컬 개발

```bash
# 1. 이미지 빌드 (선택)
./scripts/build-images.sh

# 2. 로컬 배포
./scripts/deploy-local.sh

# 3. 로그 확인
docker-compose logs -f
```

### 시나리오 3: 프로덕션 배포

```bash
# 1. 이미지 빌드 및 레지스트리 푸시
PUSH_IMAGES=1 ./scripts/build-images.sh v1.0.0 myregistry.azurecr.io

# 2. 프로덕션 배포
REGISTRY=myregistry.azurecr.io VERSION=v1.0.0 ./scripts/deploy-k8s-cloud.sh

# 3. 헬스 체크
./scripts/health-check.sh

# 4. 로그 확인
./scripts/view-logs.sh
```

### 시나리오 4: Cloudflare Tunnel 사용

```bash
# 1. 로컬 배포
./scripts/deploy-local.sh

# 2. Cloudflare Tunnel 시작
./scripts/start-tunnel.sh
# Quick Tunnel 선택 → 임시 URL 생성

# 3. Jira Webhook에 URL 등록
# 예: https://xxx.trycloudflare.com/webhook
```

---

## 📋 스크립트 종속성 매트릭스

| 스크립트 | 독립 실행 | 다른 스크립트 호출 | 호출됨 (by) |
|---------|---------|----------------|------------|
| `minikube-setup.sh` | ✅ | ❌ | ❌ |
| `build-images.sh` | ✅ | ❌ | ❌ |
| `deploy-local.sh` | ✅ | ❌ | ❌ |
| `deploy-k8s-local.sh` | ✅ | ✅ create-secrets-from-env.sh | ❌ |
| `deploy-k8s-cloud.sh` | ✅ | ✅ create-secrets-from-env.sh | ❌ |
| `create-secrets-from-env.sh` | ✅ | ❌ | ✅ deploy-k8s-* |
| `health-check.sh` | ✅ | ❌ | ❌ |
| `view-logs.sh` | ✅ | ❌ | ❌ |
| `start-tunnel.sh` | ✅ | ❌ | ❌ |

---

## 🔗 호출 관계 상세

### `deploy-k8s-local.sh` → `create-secrets-from-env.sh`

```bash
# deploy-k8s-local.sh (line 59-65)
if [ -f .env ]; then
    echo -e "${BLUE}📄 .env 파일 발견! 자동으로 Secret을 생성합니다.${NC}"
    
    if [ -f ./scripts/create-secrets-from-env.sh ]; then
        ./scripts/create-secrets-from-env.sh --auto
    fi
fi
```

**조건**:
- `.env` 파일 존재
- Secret이 아직 생성되지 않음
- `create-secrets-from-env.sh` 스크립트 존재

**동작**:
- `--auto` 플래그로 자동 모드 실행
- 확인 프롬프트 없이 자동으로 Secret 생성

### `deploy-k8s-cloud.sh` → `create-secrets-from-env.sh`

```bash
# deploy-k8s-cloud.sh (line 54-60)
if [ -f .env ]; then
    echo -e "${BLUE}📄 .env 파일 발견! 자동으로 Secret을 생성합니다.${NC}"
    
    if [ -f ./scripts/create-secrets-from-env.sh ]; then
        ./scripts/create-secrets-from-env.sh --auto
    fi
fi
```

**조건**: 동일 (deploy-k8s-local.sh와 같음)

---

## 💡 모범 사례 (Best Practices)

### 1. 환경 변수 관리

**권장 방법**:
```bash
# .env 파일 생성
cp env.example .env

# 실제 값 입력
vim .env

# Secret 자동 생성 (K8s 배포 시)
./scripts/deploy-k8s-local.sh  # 자동으로 create-secrets-from-env.sh 호출
```

**수동 방법**:
```bash
# Secret 먼저 생성
./scripts/create-secrets-from-env.sh

# 배포
./scripts/deploy-k8s-local.sh
```

### 2. 개발 워크플로우

**로컬 개발 (빠른 반복)**:
```bash
# Docker Compose 사용 (가장 빠름)
./scripts/deploy-local.sh
docker-compose logs -f

# 코드 수정 후
docker-compose restart
```

**Kubernetes 테스트**:
```bash
# Minikube 사용
./scripts/minikube-setup.sh
./scripts/build-images.sh
./scripts/deploy-k8s-local.sh

# 이미지 재빌드 후
./scripts/build-images.sh
kubectl rollout restart deployment -n agent-system
```

### 3. 프로덕션 배포

**체크리스트**:
- [ ] `.env` 파일 준비 및 검증
- [ ] Docker 이미지 빌드 및 레지스트리 푸시
- [ ] Kubernetes 클러스터 접근 확인
- [ ] kubectl 컨텍스트 확인
- [ ] Secret 생성 확인
- [ ] Ingress 및 DNS 설정
- [ ] TLS 인증서 설정
- [ ] 모니터링 설정

**배포 명령**:
```bash
# 1. 이미지 푸시
PUSH_IMAGES=1 ./scripts/build-images.sh v1.0.0 myregistry.azurecr.io

# 2. 배포
REGISTRY=myregistry.azurecr.io VERSION=v1.0.0 ./scripts/deploy-k8s-cloud.sh

# 3. 검증
./scripts/health-check.sh
kubectl get all -n agent-system
```

### 4. 트러블슈팅

**로그 확인**:
```bash
# 대화형 로그 뷰어
./scripts/view-logs.sh

# 또는 직접 명령
kubectl logs -f deployment/router-agent -n agent-system
kubectl logs -f deployment/sdb-agent -n agent-system
```

**헬스 체크**:
```bash
./scripts/health-check.sh
```

**Pod 상태 확인**:
```bash
kubectl get pods -n agent-system
kubectl describe pod <pod-name> -n agent-system
```

**Secret 확인**:
```bash
kubectl get secret agent-secrets -n agent-system
kubectl describe secret agent-secrets -n agent-system

# Bitbucket Token 확인
kubectl get secret agent-secrets -n agent-system -o jsonpath='{.data.bitbucket-access-token}' | base64 -d | head -c 20
```

---

## 🚨 주의사항

### Bitbucket 토큰
⚠️ **중요**: `BITBUCKET_ACCESS_TOKEN`은 반드시 **Bitbucket App Password**를 사용하세요!
- ✅ 올바른 토큰: `ATCTT...` (Bitbucket App Password)
- ❌ 잘못된 토큰: `ATATT...` (Jira API Token)

**생성 방법**:
1. Bitbucket → Settings → Personal settings
2. App passwords → Create app password
3. 권한: Repository Read, Write 선택

### kubectl 컨텍스트
프로덕션 배포 전 항상 kubectl 컨텍스트를 확인하세요:
```bash
kubectl config current-context
kubectl config get-contexts
```

잘못된 클러스터에 배포하지 않도록 주의!

### Secret 관리
- `.env` 파일은 **절대 Git에 커밋하지 마세요**
- `.gitignore`에 `.env` 추가 확인
- 프로덕션 Secret은 별도의 안전한 방법으로 관리 (예: Vault, AWS Secrets Manager)

---

## 📚 추가 문서

- [Kubernetes Cloud Deploy Guide](../deploy/kubernetes-cloud-deploy.md)
- [Quick Start Guide](../deploy/quick-start.md)
- [Railway Deploy Guide](../deploy/railway-deploy.md)
- [Cloudflare Tunnel Guide](../deploy/cloudflare-tunnel.md)
- [Kubernetes Secret Automation](../KUBERNETES_SECRET_AUTOMATION.md)
- [Minikube Deployment Guide](../MINIKUBE_DEPLOYMENT.md)

---

## 🆘 문제 해결

### Minikube가 시작되지 않음
```bash
minikube delete
minikube start --cpus=4 --memory=8192 --driver=docker
```

### Secret 생성 실패
```bash
# 수동으로 Secret 생성
kubectl create namespace agent-system
kubectl create secret generic agent-secrets \
  --from-literal=openai-api-key='sk-...' \
  --from-literal=bitbucket-access-token='ATCTT...' \
  --from-literal=bitbucket-username='your@email.com' \
  -n agent-system
```

### 이미지를 찾을 수 없음 (ImagePullBackOff)
```bash
# Minikube 환경 확인
eval $(minikube docker-env)
docker images | grep -E "router-agent|sdb-agent"

# 이미지 재빌드
./scripts/build-images.sh
```

### Port Forward가 작동하지 않음
```bash
# 기존 Port Forward 종료
pkill -f "kubectl port-forward"

# 새로 시작
kubectl port-forward svc/router-agent-svc 5000:5000 -n agent-system
```

---

**마지막 업데이트**: 2025-10-22
**버전**: 1.0.0

