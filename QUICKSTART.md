# Multi-Agent System - 빠른 시작 가이드

본 가이드는 Multi-Agent 시스템을 가장 빠르게 시작하는 방법을 안내합니다.

## 🎯 목표

- **로컬 환경**: 5-10분 안에 Docker Compose로 시스템 실행
- **Kubernetes (Minikube)**: 15-20분 안에 로컬 Kubernetes 클러스터 배포
- **프로덕션 (Cloud)**: Helm Chart로 클라우드 Kubernetes 배포

## 📋 사전 준비

### 필수 항목
- Windows 10/11 (WSL2 지원) 또는 Linux/macOS
- Git
- 텍스트 에디터

### 배포 방식별 요구사항
| 배포 방식 | 요구사항 |
|---------|---------|
| **로컬 (Docker Compose)** | Docker, Docker Compose |
| **로컬 (Kubernetes)** | Docker, Minikube, kubectl, Helm |
| **클라우드 (Kubernetes)** | kubectl, Helm, 클라우드 접근 권한 |

### API 키 및 토큰
- **OpenAI API 키**: GPT-4 또는 GPT-3.5 사용 권한
- **Bitbucket App Password**: `ATCTT`로 시작하는 토큰 (Jira API Token `ATATT`와 다름!)

---

## 📚 빠른 시작 방법 선택

### 방법 1: 로컬 환경 (Docker Compose) - 가장 간단 ⭐️ 추천
가장 빠르고 간단한 방법입니다. 개발 및 테스트에 적합합니다.

### 방법 2: 로컬 Kubernetes (Minikube) - 학습용
Kubernetes 환경을 로컬에서 테스트할 때 사용합니다.

### 방법 3: 클라우드 Kubernetes - 프로덕션
실제 서비스 배포를 위한 방법입니다.

---

## 🚀 방법 1: 로컬 환경 (Docker Compose)

### 사전 준비

**Windows (WSL2)**:
```powershell
# PowerShell을 관리자 권한으로 실행
wsl --install

# 재부팅 후 Ubuntu 설치 확인
wsl --list --verbose
```

**Docker 설치**:
```bash
# WSL Ubuntu / Linux 터미널에서 실행
sudo apt update
sudo apt install -y docker.io docker-compose-plugin

# 현재 사용자를 docker 그룹에 추가
sudo usermod -aG docker $USER
newgrp docker

# Docker 서비스 시작
sudo service docker start

# 설치 확인
docker --version
docker compose version
```

### 단계별 실행

#### 1단계: 프로젝트 클론 및 환경 변수 설정

```bash
# 프로젝트 디렉터리로 이동
cd /path/to/GenerateSDBAgent_Applying_k8s

# 환경 변수 파일 생성
cp env.example .env

# .env 파일 편집
nano .env
```

**필수 환경 변수**:
```env
# OpenAI 설정
OPENAI_API_KEY=sk-your-openai-api-key-here

# Bitbucket 설정
BITBUCKET_USERNAME=your-username
BITBUCKET_ACCESS_TOKEN=your-bitbucket-app-password
BITBUCKET_WORKSPACE=mit_dev
BITBUCKET_REPOSITORY=genw_new
BITBUCKET_URL=https://api.bitbucket.org
```

> ⚠️ **중요**: `BITBUCKET_ACCESS_TOKEN`은 Bitbucket App Password(`ATCTT`로 시작)를 사용해야 합니다. Jira API Token(`ATATT`)과 다릅니다!

#### 2단계: 시스템 시작

**스크립트 사용 (권장)**:
```bash
# 자동으로 이미지 빌드 및 시작
bash scripts/deploy-local.sh
```

**또는 수동으로**:
```bash
# Docker 이미지 빌드
bash scripts/build-images.sh

# Docker Compose 시작
docker compose up -d

# 상태 확인
docker compose ps
```

#### 3단계: 동작 확인

```bash
# 헬스 체크
curl http://localhost:5000/health

# Agent 목록 확인
curl http://localhost:5000/agents
```

**브라우저에서 확인**:
- Health: http://localhost:5000/health
- Agents: http://localhost:5000/agents

#### 4단계: 로그 확인

```bash
# 스크립트로 로그 확인 (권장)
bash scripts/view-logs.sh

# 또는 직접 명령어
docker compose logs -f router-agent
docker compose logs -f sdb-agent
```

### 헬스 체크

```bash
# 전체 헬스 체크
bash scripts/health-check.sh

# 수동으로 헬스 체크
curl http://localhost:5000/health | jq .
```

### 시스템 중지

```bash
# 컨테이너 중지 및 제거
docker compose down

# 볼륨까지 제거
docker compose down -v
```

---

## 🚀 방법 2: 로컬 Kubernetes (Minikube)

Kubernetes 환경을 로컬에서 실습하고 테스트할 수 있습니다.

### 사전 준비

#### 1. Minikube 설치

**Windows**:
```powershell
choco install minikube
```

**macOS**:
```bash
brew install minikube
```

**Linux**:
```bash
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube
```

#### 2. kubectl 설치

**Windows**:
```powershell
choco install kubernetes-cli
```

**macOS**:
```bash
brew install kubectl
```

**Linux**:
```bash
sudo snap install kubectl --classic
```

#### 3. Helm 설치

**Windows**:
```powershell
choco install kubernetes-helm
```

**macOS**:
```bash
brew install helm
```

**Linux**:
```bash
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

### 단계별 실행

#### 1단계: Minikube 클러스터 시작

```bash
# 스크립트로 자동 설정 (권장)
bash scripts/minikube-setup.sh
```

**스크립트가 자동으로 수행하는 작업**:
- Minikube 클러스터 시작 (CPUs: 4, Memory: 8GB)
- Ingress addon 활성화
- Metrics Server addon 활성화
- Ingress Controller 준비 대기

**수동 설정**:
```bash
# Minikube 시작
minikube start --cpus=4 --memory=8192 --driver=docker

# Addons 활성화
minikube addons enable ingress
minikube addons enable metrics-server

# 상태 확인
minikube status
kubectl cluster-info
```

#### 2단계: 환경 변수 설정

```bash
# .env 파일 생성
cp env.example .env

# .env 파일 편집
nano .env
```

**필수 환경 변수**:
```env
OPENAI_API_KEY=sk-your-openai-api-key-here
BITBUCKET_USERNAME=your-username
BITBUCKET_ACCESS_TOKEN=your-bitbucket-app-password
BITBUCKET_WORKSPACE=mit_dev
BITBUCKET_REPOSITORY=genw_new
BITBUCKET_URL=https://api.bitbucket.org
```

#### 3단계: Docker 이미지 빌드

```bash
# Minikube Docker 환경 사용
bash scripts/build-images.sh
```

**스크립트가 자동으로 수행하는 작업**:
- Minikube Docker 환경 감지 및 사용
- Router Agent 이미지 빌드
- SDB Agent 이미지 빌드

#### 4단계: Kubernetes Secret 생성 및 배포

```bash
# 자동 배포 (Secret 자동 생성 포함)
bash scripts/deploy-k8s-local.sh
```

**스크립트가 자동으로 수행하는 작업**:
1. `.env` 파일 감지
2. `create-secrets-from-env.sh` 자동 호출
3. Bitbucket 토큰 타입 검증 (ATCTT vs ATATT)
4. Kubernetes Secret 자동 생성
5. Helm Chart 배포

**Secret만 별도로 생성**:
```bash
# Secret 생성 스크립트 실행
bash scripts/create-secrets-from-env.sh

# 또는 자동 모드 (프롬프트 없이)
bash scripts/create-secrets-from-env.sh --auto
```

#### 5단계: 배포 확인

```bash
# Pod 상태 확인
kubectl get pods -n agent-system

# Service 확인
kubectl get svc -n agent-system

# Ingress 확인
kubectl get ingress -n agent-system

# 전체 헬스 체크
bash scripts/health-check.sh
```

#### 6단계: 서비스 접근

**방법 1: Port Forward (권장)**
```bash
# Port Forward 시작
kubectl port-forward svc/router-agent-svc 5000:5000 -n agent-system

# 다른 터미널에서 테스트
curl http://localhost:5000/health
```

**방법 2: Minikube Service**
```bash
# 자동으로 브라우저 열기
minikube service router-agent-svc -n agent-system
```

**방법 3: Ingress**
```bash
# Minikube Tunnel 시작 (다른 터미널에서)
minikube tunnel

# /etc/hosts 또는 C:\Windows\System32\drivers\etc\hosts에 추가
# 127.0.0.1 agents.local

# 브라우저에서 접속
# http://agents.local
```

### 로그 확인

```bash
# 스크립트로 로그 확인
bash scripts/view-logs.sh

# 또는 직접 명령어
kubectl logs -f deployment/router-agent -n agent-system
kubectl logs -f deployment/sdb-agent -n agent-system
```

### 배포 업데이트

```bash
# 코드 변경 후 재배포
bash scripts/build-images.sh
bash scripts/deploy-k8s-local.sh

# 또는 Pod만 재시작
kubectl rollout restart deployment -n agent-system
```

### 시스템 중지 및 정리

```bash
# Helm 릴리스 삭제
helm uninstall multi-agent-system -n agent-system

# Namespace 삭제
kubectl delete namespace agent-system

# Minikube 중지
minikube stop

# Minikube 완전 삭제
minikube delete
```

---

## 🚀 방법 3: 클라우드 Kubernetes (프로덕션)

실제 서비스 배포를 위한 클라우드 Kubernetes 환경에 배포합니다.

### 사전 준비

1. **Kubernetes 클러스터 접근 권한**
   - Azure AKS, AWS EKS, GCP GKE 등
   - kubectl이 클러스터에 연결되어 있어야 함

2. **Container Registry**
   - Docker Hub, Azure ACR, AWS ECR, GCP GCR 등
   - 이미지 push 권한

3. **kubectl 및 Helm 설치** (위 Minikube 섹션 참조)

### 단계별 실행

#### 1단계: kubectl 컨텍스트 확인

```bash
# 현재 컨텍스트 확인
kubectl config current-context

# 클러스터 정보 확인
kubectl cluster-info

# 사용 가능한 컨텍스트 목록
kubectl config get-contexts
```

#### 2단계: 환경 변수 설정

```bash
# .env 파일 생성
cp env.example .env

# .env 파일 편집 (프로덕션 값 입력)
nano .env
```

#### 3단계: Docker 이미지 빌드 및 Push

```bash
# 레지스트리 설정
export REGISTRY="your-registry.azurecr.io"  # 또는 docker.io/username
export VERSION="1.0.0"

# 이미지 빌드 및 Push
PUSH_IMAGES=1 bash scripts/build-images.sh $VERSION $REGISTRY
```

**또는 수동으로**:
```bash
# 이미지 빌드
docker build -t $REGISTRY/router-agent:$VERSION ./router-agent
docker build -t $REGISTRY/sdb-agent:$VERSION ./sdb-agent

# 레지스트리에 Push
docker push $REGISTRY/router-agent:$VERSION
docker push $REGISTRY/sdb-agent:$VERSION
```

#### 4단계: Kubernetes Secret 생성

```bash
# .env 파일에서 자동 생성
bash scripts/create-secrets-from-env.sh --auto
```

**또는 수동으로**:
```bash
kubectl create namespace agent-system

kubectl create secret generic agent-secrets \
  --from-literal=openai-api-key='sk-...' \
  --from-literal=bitbucket-access-token='ATCTT...' \
  --from-literal=bitbucket-username='your@email.com' \
  --from-literal=bitbucket-workspace='mit_dev' \
  --from-literal=bitbucket-repository='genw_new' \
  --from-literal=bitbucket-url='https://api.bitbucket.org' \
  -n agent-system
```

#### 5단계: 클라우드 배포

```bash
# 환경 변수 설정 후 배포 스크립트 실행
export REGISTRY="your-registry.azurecr.io"
export VERSION="1.0.0"

bash scripts/deploy-k8s-cloud.sh
```

**스크립트가 자동으로 수행하는 작업**:
1. kubectl 컨텍스트 확인
2. Secret 확인 (없으면 .env로 자동 생성)
3. Docker 이미지 확인
4. Helm Chart 배포 (production values 사용)

**수동 배포**:
```bash
helm upgrade --install multi-agent-system \
  ./helm/multi-agent-system \
  -f ./helm/multi-agent-system/values-production.yaml \
  --set imageRegistry.url=$REGISTRY \
  --set routerAgent.image.tag=$VERSION \
  --set sdbAgent.image.tag=$VERSION \
  --namespace agent-system \
  --create-namespace \
  --wait \
  --timeout 10m
```

#### 6단계: 배포 확인

```bash
# 모든 리소스 확인
kubectl get all -n agent-system

# Ingress 확인
kubectl get ingress -n agent-system

# 헬스 체크
bash scripts/health-check.sh
```

#### 7단계: DNS 및 Ingress 설정

```bash
# Ingress IP 확인
kubectl get ingress -n agent-system

# DNS 레코드 설정
# agents.your-domain.com -> Ingress EXTERNAL-IP
```

### 모니터링 및 관리

```bash
# 로그 확인
bash scripts/view-logs.sh

# Pod 상태 모니터링
kubectl get pods -n agent-system -w

# HPA (Auto Scaling) 확인
kubectl get hpa -n agent-system

# 메트릭 확인
kubectl top pods -n agent-system
```

### 배포 업데이트

```bash
# 1. 새 버전 이미지 빌드 및 Push
export VERSION="1.0.1"
PUSH_IMAGES=1 bash scripts/build-images.sh $VERSION $REGISTRY

# 2. Helm 업그레이드
bash scripts/deploy-k8s-cloud.sh

# 또는 Rolling Update
kubectl rollout restart deployment/router-agent -n agent-system
kubectl rollout restart deployment/sdb-agent -n agent-system

# 롤아웃 상태 확인
kubectl rollout status deployment/router-agent -n agent-system
```

### 시스템 중지 및 정리

```bash
# Helm 릴리스 삭제
helm uninstall multi-agent-system -n agent-system

# Namespace 삭제 (주의: 모든 리소스 삭제됨)
kubectl delete namespace agent-system
```

---

## 🧪 테스트 및 검증

### 헬스 체크

```bash
# 자동 헬스 체크 스크립트
bash scripts/health-check.sh

# 수동으로 확인
curl http://localhost:5000/health | jq .
```

**성공 응답 예시**:
```json
{
  "status": "healthy",
  "timestamp": "2025-10-26T10:00:00",
  "agents": {
    "sdb-agent": true
  },
  "router_version": "1.0.0"
}
```

### Intent Classification 테스트

```bash
curl -X POST http://localhost:5000/test-classification \
  -H "Content-Type: application/json" \
  -d '{
    "issue": {
      "fields": {
        "summary": "SDB 개발 요청: 철골 재질 추가",
        "description": "Material DB에 철골 재질을 추가해주세요"
      }
    }
  }'
```

### Webhook 테스트

```bash
# 샘플 Jira Webhook 데이터로 테스트
curl -X POST http://localhost:5000/webhook \
  -H "Content-Type: application/json" \
  -d @test/test_router_webhook.json
```

### 외부 Webhook 테스트 (Jira 연동)

**중요**: Jira Webhook은 외부 인터넷에서 접근 가능한 URL이 필요합니다. 로컬 환경(`localhost:5000`)은 Jira에서 접근할 수 없으므로, 외부 URL을 생성해야 합니다.

#### Cloudflare Tunnel 사용 (추천 🌟 무료)

**1단계: Cloudflare Tunnel 설치**

```bash
# WSL/Linux에서 설치
wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb

# 설치 확인
cloudflared --version
```

**2단계: Port Forward 실행 확인**

```bash
# Port Forward가 실행 중인지 확인
ps aux | grep "kubectl port-forward"

# Docker Compose 환경이라면 서비스가 실행 중인지 확인
docker compose ps

# 만약 실행 중이 아니라면:
# Kubernetes: kubectl port-forward svc/router-agent-svc 5000:5000 -n agent-system
# Docker Compose: docker compose up -d
```

**3단계: Quick Tunnel 시작**

```bash
# 새 터미널 창에서 실행 (Port Forward와 별도 터미널)
cloudflared tunnel --url http://localhost:5000
```

**출력 예시**:
```
INF Your quick Tunnel has been created! Visit it at (it may take some time to be reachable):
INF https://random-abc-def-123.trycloudflare.com
```

**4단계: Jira Webhook 설정**

1. Jira 관리자 페이지로 이동
2. **설정** → **시스템** → **WebHooks** 클릭
3. **Create a WebHook** 클릭
4. 다음 정보 입력:
   - **Name**: `Multi-Agent SDB System`
   - **Status**: `Enabled`
   - **URL**: `https://random-abc-def-123.trycloudflare.com/webhook` ← Cloudflare Tunnel URL 사용
   - **Events**:
     - Issue: `created`, `updated`
     - (선택) Comment: `created`
5. **Create** 클릭

**5단계: 테스트 - Jira 이슈 생성**

```
1. Jira에서 새 이슈 생성
   - Summary: "SDB 개발 요청: Material DB에 철골 재질 추가"
   - Description: "Material 테이블에 철골 재질 정보를 추가해주세요"

2. 이슈 생성 후 로그 확인:

# Kubernetes 환경:
kubectl logs -f -l app=router-agent -n agent-system --tail=50

# Docker Compose 환경:
docker compose logs -f router-agent
```

**예상 로그 출력**:
```
INFO - Received webhook from Jira
INFO - Intent classified: sdb (confidence: 0.95)
INFO - Routing to SDB Agent
INFO - SDB Agent processing started
INFO - PR created successfully
```

**6단계: Bitbucket에서 PR 확인**

Jira 이슈가 처리되면 Bitbucket에 자동으로 Pull Request가 생성됩니다:
```
https://bitbucket.org/mit_dev/genw_new/pull-requests/
```

#### 대안: ngrok 사용

ngrok은 설치가 간편하지만 무료 버전은 URL이 계속 변경됩니다.

```bash
# ngrok 설치 (WSL/Linux)
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | \
  sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null && \
  echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | \
  sudo tee /etc/apt/sources.list.d/ngrok.list && \
  sudo apt update && sudo apt install ngrok

# ngrok 실행
ngrok http 5000

# 출력된 URL을 Jira Webhook에 설정
# https://abc123.ngrok-free.app/webhook
```

#### 터널 종료

작업이 끝나면 터널을 종료할 수 있습니다:

```bash
# Cloudflare Tunnel 실행 중인 터미널에서 Ctrl+C

# 또는 프로세스 강제 종료
pkill -f cloudflared
```

#### 주의사항

⚠️ **보안**: Quick Tunnel은 누구나 접근 가능한 공개 URL입니다.
- 실제 운영 환경에서는 인증 토큰 검증을 추가하거나
- Named Tunnel(고정 URL)과 Access Policy를 사용하세요
- 테스트 완료 후 터널을 종료하세요

⚠️ **URL 변경**: Quick Tunnel URL은 재시작할 때마다 변경됩니다.
- Jira Webhook URL도 매번 업데이트 필요
- 고정 URL이 필요하면 Cloudflare Named Tunnel 사용 ([deploy/cloudflare-tunnel.md](deploy/cloudflare-tunnel.md) 참조)

---

## 🐛 문제 해결

### 공통 문제

#### Docker 서비스가 시작되지 않음

```bash
# WSL/Linux에서 Docker 서비스 상태 확인
sudo service docker status

# Docker 서비스 시작
sudo service docker start

# Docker 데몬이 실행 중인지 확인
docker ps
```

#### 컨테이너가 시작되지 않음

```bash
# 로그 확인
docker compose logs

# 특정 컨테이너 로그
docker compose logs router-agent
docker compose logs sdb-agent

# 강제 재빌드 및 재시작
docker compose down
docker compose up -d --build
```

#### Port 5000이 이미 사용 중

```bash
# docker-compose.yml 편집하여 포트 변경
nano docker-compose.yml
# ports:
#   - "5001:5000"  # 5001로 변경

docker compose up -d
curl http://localhost:5001/health
```

#### OpenAI API 키 오류

```bash
# .env 파일에 API 키가 올바르게 설정되어 있는지 확인
cat .env | grep OPENAI_API_KEY

# 환경 변수 재로드를 위해 컨테이너 재시작
docker compose restart
```

### Kubernetes 관련 문제

#### Pod가 시작되지 않음

```bash
# Pod 상태 확인
kubectl get pods -n agent-system

# Pod 상세 정보 확인
kubectl describe pod <pod-name> -n agent-system

# Pod 로그 확인
kubectl logs <pod-name> -n agent-system

# 이벤트 확인
kubectl get events -n agent-system --sort-by='.lastTimestamp'
```

#### ImagePullBackOff 오류

```bash
# 이미지가 Minikube Docker 환경에 있는지 확인
eval $(minikube docker-env)
docker images | grep -E "router-agent|sdb-agent"

# 이미지 재빌드
bash scripts/build-images.sh

# Pod 재시작
kubectl rollout restart deployment -n agent-system
```

#### Secret 관련 오류

```bash
# Secret 존재 확인
kubectl get secret agent-secrets -n agent-system

# Secret 내용 확인
kubectl get secret agent-secrets -n agent-system -o yaml

# Secret 재생성
kubectl delete secret agent-secrets -n agent-system
bash scripts/create-secrets-from-env.sh --auto
```

#### Bitbucket 토큰 오류

```bash
# 토큰 타입 확인
kubectl get secret agent-secrets -n agent-system \
  -o jsonpath='{.data.bitbucket-access-token}' | base64 -d | cut -c1-5
# ATCTT 출력되어야 함 (ATATT는 잘못된 토큰)

# .env 파일 확인 및 수정
cat .env | grep BITBUCKET_ACCESS_TOKEN

# Secret 재생성
bash scripts/create-secrets-from-env.sh --auto
kubectl rollout restart deployment -n agent-system
```

### WSL 관련 문제

#### 권한 오류 (Permission denied)

```bash
# docker 그룹 재적용 (그룹 추가 후)
newgrp docker

# 또는 WSL 재시작
# PowerShell에서:
# wsl --shutdown
# wsl
```

#### 스크립트 실행 권한 오류

```bash
# 스크립트 실행 권한 부여
chmod +x scripts/*.sh

# 확인
ls -la scripts/
```

#### WSL에서 Windows 포트 접근 안 됨

```bash
# Windows 방화벽 확인 필요
# PowerShell 관리자 권한으로:
# New-NetFirewallRule -DisplayName "WSL" -Direction Inbound -InterfaceAlias "vEthernet (WSL)" -Action Allow

# WSL에서 localhost 대신 Windows IP 사용
ip route show | grep default | awk '{print $3}'
```

#### 파일 권한 문제

```bash
# WSL 파일 시스템으로 이동하는 것을 권장 (성능 및 권한 문제 해결)
cp -r /mnt/c/MIDAS/10_Source/GenerateSDBAgent_Applying_k8s ~/
cd ~/GenerateSDBAgent_Applying_k8s
```

---

## 📊 스크립트 사용 가이드

프로젝트의 `scripts/` 디렉터리에는 배포 및 관리를 자동화하는 스크립트들이 있습니다.

### 사용 가능한 스크립트

| 스크립트 | 설명 | 사용 시기 |
|---------|------|----------|
| `build-images.sh` | Docker 이미지 빌드 | 코드 변경 후 이미지 재빌드 |
| `deploy-local.sh` | Docker Compose 배포 | 로컬 환경 시작 |
| `minikube-setup.sh` | Minikube 초기 설정 | Minikube 최초 설치 및 설정 |
| `create-secrets-from-env.sh` | Kubernetes Secret 생성 | .env에서 Secret 자동 생성 |
| `deploy-k8s-local.sh` | Minikube 배포 | 로컬 Kubernetes 배포 |
| `deploy-k8s-cloud.sh` | 클라우드 배포 | 프로덕션 Kubernetes 배포 |
| `health-check.sh` | 헬스 체크 | 시스템 상태 확인 |
| `view-logs.sh` | 로그 확인 | 실시간 로그 모니터링 |
| `start-tunnel.sh` | Cloudflare Tunnel | 외부 접근용 터널 시작 |

### 스크립트 사용 예시

#### 1. 로컬 환경 전체 설정

```bash
# 1단계: 환경 변수 설정
cp env.example .env
nano .env

# 2단계: 이미지 빌드 및 시작
bash scripts/deploy-local.sh

# 3단계: 헬스 체크
bash scripts/health-check.sh

# 4단계: 로그 확인
bash scripts/view-logs.sh
```

#### 2. Minikube 환경 전체 설정

```bash
# 1단계: Minikube 초기 설정
bash scripts/minikube-setup.sh

# 2단계: 환경 변수 설정
cp env.example .env
nano .env

# 3단계: 이미지 빌드
bash scripts/build-images.sh

# 4단계: Kubernetes 배포 (Secret 자동 생성)
bash scripts/deploy-k8s-local.sh

# 5단계: 헬스 체크
bash scripts/health-check.sh
```

#### 3. 코드 변경 후 재배포

**Docker Compose 환경**:
```bash
# 이미지 재빌드
bash scripts/build-images.sh

# 재시작
docker compose restart

# 또는 전체 재배포
bash scripts/deploy-local.sh
```

**Kubernetes 환경**:
```bash
# 이미지 재빌드
bash scripts/build-images.sh

# Pod 재시작
kubectl rollout restart deployment -n agent-system

# 또는 전체 재배포
bash scripts/deploy-k8s-local.sh
```

#### 4. 프로덕션 배포

```bash
# 1단계: 환경 변수 설정
export REGISTRY="your-registry.azurecr.io"
export VERSION="1.0.0"

# 2단계: 이미지 빌드 및 Push
PUSH_IMAGES=1 bash scripts/build-images.sh $VERSION $REGISTRY

# 3단계: kubectl 컨텍스트 확인
kubectl config current-context

# 4단계: Secret 생성
bash scripts/create-secrets-from-env.sh --auto

# 5단계: 배포
bash scripts/deploy-k8s-cloud.sh
```

---

## 💡 유용한 팁

### WSL 작업 효율화

**Docker 서비스 자동 시작**:
```bash
# ~/.bashrc 또는 ~/.zshrc에 추가
if ! service docker status > /dev/null 2>&1; then
    sudo service docker start
fi
```

**Windows 탐색기에서 WSL 폴더 열기**:
```bash
# WSL에서 현재 디렉터리를 Windows 탐색기로 열기
explorer.exe .
```

**VS Code에서 WSL 프로젝트 열기**:
```bash
# WSL에서 실행
code .
```

**WSL 메모리 제한 설정** (선택사항):
```powershell
# Windows에서 %UserProfile%\.wslconfig 생성
[wsl2]
memory=4GB
processors=2
```

### 개발 워크플로우

#### 코드 변경 시 자동 반영

Docker Compose의 volumes 설정으로 코드 변경사항이 자동 반영됩니다:

```yaml
volumes:
  - ./sdb-agent/app:/app/app:ro
```

Python 파일 변경 시 컨테이너 재시작:
```bash
docker compose restart sdb-agent
```

#### 빠른 테스트 사이클

```bash
# 1. 코드 수정
nano sdb-agent/app/main.py

# 2. 컨테이너 재시작
docker compose restart sdb-agent

# 3. 로그 확인
docker compose logs -f sdb-agent

# 4. 테스트
curl http://localhost:5000/health
```

### 성능 최적화

1. **WSL 파일 시스템 사용**
   - `/home` 사용 (Windows 파일 시스템보다 10배 빠름)
   - Git clone을 WSL에서 직접 수행
   
2. **Docker 빌드 캐시**
   - WSL 파일 시스템에서 빌드 시 캐시 효율 향상
   - 불필요한 파일 제외 (.dockerignore 활용)

3. **Minikube 리소스 조정**
   ```bash
   minikube start --cpus=4 --memory=8192 --disk-size=20g
   ```

### 디버깅 팁

#### 상세 로그 활성화

```bash
# .env 파일에서 로그 레벨 변경
LOG_LEVEL=DEBUG

# 컨테이너 재시작
docker compose restart
```

#### 컨테이너 내부 접근

```bash
# Docker Compose
docker compose exec sdb-agent bash

# Kubernetes
kubectl exec -it deployment/sdb-agent -n agent-system -- bash
```

#### 네트워크 디버깅

```bash
# Docker Compose 네트워크 확인
docker compose ps
docker network ls

# Kubernetes Service 디버깅
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -- sh
# 컨테이너 내부에서:
# curl router-agent-svc:5000/health
```

---

## 📚 추가 문서

### 프로젝트 문서
- [전체 README](README.md)
- [Router Agent](router-agent/README.md)
- [SDB Agent](sdb-agent/README.md)
- [Helm Chart](helm/multi-agent-system/README.md)

### 아키텍처 및 설계
- [Multi-Agent 아키텍처](sdb-agent/doc/MULTI_AGENT_ARCHITECTURE.md)
- [프로세스 플로우](sdb-agent/doc/PROCESS_FLOW.md)

### Kubernetes 관련
- [Minikube 배포 가이드](docs/kubernetes/MINIKUBE_DEPLOYMENT.md)
- [Secret 자동화](docs/kubernetes/KUBERNETES_SECRET_AUTOMATION.md)
- [Secret 트러블슈팅](docs/kubernetes/KUBERNETES_SECRET_TROUBLESHOOTING.md)

### 배포 가이드
- [Railway 배포](deploy/railway-deploy.md)
- [Cloudflare Tunnel](deploy/cloudflare-tunnel.md)
- [클라우드 Kubernetes 배포](deploy/kubernetes-cloud-deploy.md)

---

## ❓ FAQ

**Q: WSL2와 Docker Desktop의 차이는?**  
A: WSL2는 더 가볍고 리소스 효율적이며, Windows와 Linux 통합이 뛰어납니다. Docker Desktop은 GUI가 있지만 더 무겁고 유료 라이선스가 필요할 수 있습니다.

**Q: WSL에서 Docker가 느린 것 같아요**  
A: Windows 파일 시스템(`/mnt/c/`)이 아닌 WSL 파일 시스템(`/home/`)을 사용하세요. 성능이 크게 개선됩니다.

**Q: Docker Compose와 Kubernetes의 차이는?**  
A: Docker Compose는 로컬 개발용으로 간단하고 빠릅니다. Kubernetes는 프로덕션 배포용으로 확장성과 관리 기능이 뛰어납니다.

**Q: Minikube에서 개발한 것을 클라우드에 배포할 수 있나?**  
A: 네! Helm Chart를 사용하면 거의 동일하게 배포 가능합니다. values 파일만 변경하면 됩니다.

**Q: 새로운 Agent를 추가하려면?**  
A: 1) 새 Agent 개발 → 2) Router의 `intent_classifier.py` 및 `agent_registry.py` 수정 → 3) Helm Chart 업데이트 → 4) 배포

**Q: WSL 재부팅 후 Docker가 실행 안 됨**  
A: WSL에서 Docker는 자동 시작되지 않습니다. `sudo service docker start`를 실행하거나 `~/.bashrc`에 자동 시작 스크립트를 추가하세요.

**Q: Bitbucket App Password와 Jira API Token의 차이는?**  
A: Bitbucket App Password는 `ATCTT`로 시작하며 Bitbucket API 전용입니다. Jira API Token은 `ATATT`로 시작하며 Jira API 전용입니다. 각각 다른 서비스에서 사용해야 합니다.

**Q: 스크립트 실행 시 "Permission denied" 오류가 발생해요**  
A: `chmod +x scripts/*.sh`로 실행 권한을 부여하세요.

**Q: Port Forward가 끊기지 않고 유지하려면?**  
A: `nohup kubectl port-forward svc/router-agent-svc 5000:5000 -n agent-system &` 명령어를 사용하거나, Ingress를 설정하세요.

**Q: 로컬 개발 시 코드 변경이 반영 안 돼요**  
A: Docker Compose는 volume mount로 자동 반영되지만, Python 프로세스 재시작이 필요할 수 있습니다. `docker compose restart <service-name>`을 실행하세요.

**Q: 비용은?**  
A: 로컬(WSL2 + Minikube): 무료, 클라우드: 리소스 사용량에 따라 과금 (Compute, Storage, Network)

---

## 🎓 다음 단계

### 1. Agent 개발 심화
- 새로운 Agent 추가
- Intent Classification 로직 개선
- Few-shot Learning 예제 추가

### 2. 모니터링 설정
- Prometheus + Grafana 대시보드 구성
- 로그 집계 시스템 (ELK Stack 또는 Loki)
- Alert 규칙 설정

### 3. 프로덕션 준비
- 환경 변수 검증 강화
- Secret 관리 (외부 Secret Manager 연동)
- CI/CD 파이프라인 구축
- 백업 및 재해 복구 계획

### 4. 확장성 개선
- Auto Scaling 설정 (HPA, VPA)
- Load Balancer 구성
- Database 최적화 (Redis, PostgreSQL 연동)

### 5. 보안 강화
- Network Policy 설정
- RBAC 구성
- Pod Security Policy
- 이미지 취약점 스캔

---

## 🆘 도움말

문제가 있거나 질문이 있으면:

1. **문서 확인**: `docs/` 디렉터리의 상세 가이드 참조
2. **로그 확인**: `bash scripts/view-logs.sh`로 실시간 로그 확인
3. **헬스 체크**: `bash scripts/health-check.sh`로 시스템 상태 진단
4. **GitHub Issues**: 버그 리포트 및 기능 요청
5. **팀 커뮤니케이션**: Slack 또는 팀 채널

---

**즐거운 개발 되세요!** 🎉

---

## 📝 부록: 스크립트 상세 설명

### `build-images.sh`

**기능**: Docker 이미지를 빌드하고 선택적으로 레지스트리에 푸시합니다.

**사용법**:
```bash
# 기본 사용 (latest 태그, Minikube Docker 환경)
bash scripts/build-images.sh

# 버전 지정
bash scripts/build-images.sh v1.0.0

# 레지스트리 지정
bash scripts/build-images.sh v1.0.0 your-registry.azurecr.io

# 이미지 푸시
PUSH_IMAGES=1 bash scripts/build-images.sh v1.0.0 your-registry.azurecr.io
```

**옵션**:
- `VERSION`: 이미지 태그 (기본값: `latest`)
- `REGISTRY`: 컨테이너 레지스트리 URL (기본값: `docker.io`)
- `USE_MINIKUBE`: Minikube Docker 환경 사용 여부 (기본값: `true`)
- `PUSH_IMAGES`: 이미지 푸시 여부 (환경 변수로 설정)

### `create-secrets-from-env.sh`

**기능**: `.env` 파일에서 Kubernetes Secret을 자동으로 생성합니다.

**사용법**:
```bash
# 대화형 모드 (프롬프트 표시)
bash scripts/create-secrets-from-env.sh

# 자동 모드 (프롬프트 없이)
bash scripts/create-secrets-from-env.sh --auto
```

**검증 기능**:
- `.env` 파일 존재 확인
- 필수 환경 변수 확인
- Bitbucket 토큰 타입 검증 (ATCTT vs ATATT)
- Secret 생성 후 검증

### `minikube-setup.sh`

**기능**: Minikube 클러스터를 초기 설정합니다.

**사용법**:
```bash
bash scripts/minikube-setup.sh
```

**수행 작업**:
- Minikube 시작 (CPUs: 4, Memory: 8GB)
- Ingress addon 활성화
- Metrics Server addon 활성화
- Ingress Controller 준비 대기

### `deploy-local.sh`

**기능**: Docker Compose로 로컬 환경에 배포합니다.

**사용법**:
```bash
bash scripts/deploy-local.sh
```

**수행 작업**:
- `.env` 파일 확인 (없으면 `env.example`에서 복사)
- Docker Compose 시작
- 헬스 체크 수행

### `deploy-k8s-local.sh`

**기능**: Minikube에 Helm Chart를 배포합니다.

**사용법**:
```bash
bash scripts/deploy-k8s-local.sh
```

**수행 작업**:
- Minikube 상태 확인
- Secret 확인 (없으면 `.env`에서 자동 생성)
- Helm Chart 배포 (`values-local.yaml` 사용)
- Port Forward 옵션 제공

### `deploy-k8s-cloud.sh`

**기능**: 클라우드 Kubernetes에 Helm Chart를 배포합니다.

**사용법**:
```bash
export REGISTRY="your-registry.azurecr.io"
export VERSION="1.0.0"
bash scripts/deploy-k8s-cloud.sh
```

**수행 작업**:
- kubectl 컨텍스트 확인 (프로덕션 경고)
- Secret 확인 (없으면 자동 생성 또는 오류)
- Docker 이미지 확인
- Helm Chart 배포 (`values-production.yaml` 사용)

### `health-check.sh`

**기능**: Multi-Agent 시스템의 헬스를 체크합니다.

**사용법**:
```bash
bash scripts/health-check.sh
```

**지원 환경**:
- Docker Compose
- Kubernetes (자동 감지)

**확인 항목**:
- 컨테이너/Pod 상태
- Router Agent 헬스 엔드포인트
- SDB Agent 헬스 엔드포인트
- HPA 상태 (Kubernetes)

### `view-logs.sh`

**기능**: Agent 로그를 실시간으로 확인합니다.

**사용법**:
```bash
bash scripts/view-logs.sh
```

**옵션**:
1. Router Agent 로그
2. SDB Agent 로그
3. 모든 Agent 로그 (실시간)
4. 최근 로그 (100줄)

**지원 환경**:
- Docker Compose
- Kubernetes (자동 감지)

### `start-tunnel.sh`

**기능**: Cloudflare Tunnel을 시작하여 외부에서 로컬 서비스에 접근할 수 있게 합니다.

**사용법**:
```bash
bash scripts/start-tunnel.sh
```

**옵션**:
1. Quick Tunnel (임시 URL)
2. Named Tunnel (고정 URL, 설정 필요)

**사용 사례**:
- Jira Webhook 테스트
- 외부 클라이언트 데모
- 원격 접근

---

## 📋 체크리스트

### 초기 설정 체크리스트

- [ ] WSL2 설치 및 설정 (Windows 사용자)
- [ ] Docker 설치 및 실행
- [ ] Git 설치
- [ ] 텍스트 에디터 준비
- [ ] OpenAI API 키 발급
- [ ] Bitbucket App Password 생성 (ATCTT)
- [ ] `.env` 파일 생성 및 설정
- [ ] 스크립트 실행 권한 부여 (`chmod +x scripts/*.sh`)

### Docker Compose 배포 체크리스트

- [ ] `.env` 파일 설정 완료
- [ ] Docker 서비스 실행 중
- [ ] `bash scripts/deploy-local.sh` 실행
- [ ] `http://localhost:5000/health` 접근 가능
- [ ] Agent 목록 확인 (`/agents`)
- [ ] 로그 정상 출력 확인

### Kubernetes 배포 체크리스트

- [ ] Minikube/kubectl/Helm 설치
- [ ] Minikube 클러스터 시작 (`minikube-setup.sh`)
- [ ] `.env` 파일 설정 완료
- [ ] Docker 이미지 빌드 완료
- [ ] Kubernetes Secret 생성 완료
- [ ] Helm Chart 배포 완료
- [ ] Pod 상태 `Running` 확인
- [ ] Port Forward 또는 Ingress 설정
- [ ] 헬스 체크 통과

### 프로덕션 배포 체크리스트

- [ ] 컨테이너 레지스트리 준비
- [ ] Kubernetes 클러스터 접근 권한
- [ ] 프로덕션 `.env` 설정
- [ ] Docker 이미지 빌드 및 푸시
- [ ] Kubernetes Secret 생성
- [ ] DNS 레코드 설정
- [ ] TLS 인증서 설정
- [ ] Ingress 구성
- [ ] 모니터링 설정
- [ ] 백업 전략 수립
- [ ] Helm Chart 배포
- [ ] 헬스 체크 및 부하 테스트
- [ ] 롤백 계획 수립

---