# 개발환경 세팅 상세 가이드

이 문서는 GenerateSDBAgent 프로젝트의 개발환경을 처음부터 구축하는 방법을 설명합니다.

## 목차

- [Phase 1: Windows 기본 환경 (WSL2 + Docker)](#phase-1-windows-기본-환경-wsl2--docker)
- [Phase 2: 개발 도구 설치](#phase-2-개발-도구-설치)
- [Phase 3: 프로젝트 설정](#phase-3-프로젝트-설정)
- [Phase 4: 실행 및 검증](#phase-4-실행-및-검증)
- [추가 설정](#추가-설정)
- [트러블슈팅](#트러블슈팅)
- [전체 명령어 요약](#전체-명령어-요약-복사용)

---

## Phase 1: Windows 기본 환경 (WSL2 + Docker)

### 1. Windows WSL2 활성화 및 Ubuntu 설치

#### 1-1. WSL2 기능 활성화 (PowerShell 관리자 권한)

```powershell
# PowerShell을 관리자 권한으로 실행 후

# WSL 기능 활성화
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart

# 가상 머신 플랫폼 활성화
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

# 재부팅 필요
shutdown /r /t 0
```

#### 1-2. 재부팅 후 WSL2 설정

```powershell
# PowerShell 관리자 권한

# WSL2를 기본 버전으로 설정
wsl --set-default-version 2

# WSL 커널 업데이트 (필요한 경우)
wsl --update

# Ubuntu 22.04 설치
wsl --install -d Ubuntu-22.04
```

#### 1-3. Ubuntu 초기 설정

설치 후 Ubuntu 터미널이 열리면:

```bash
# 사용자 이름과 비밀번호 설정 (프롬프트에 따라 입력)
# Enter new UNIX username: [원하는 사용자명]
# New password: [비밀번호]
```

#### 1-4. WSL 설정 확인

```powershell
# PowerShell에서 확인
wsl -l -v

# 출력 예시:
#   NAME            STATE           VERSION
# * Ubuntu-22.04    Running         2
```

---

### 2. WSL Ubuntu 기본 패키지 설치

#### 2-1. 시스템 업데이트

```bash
# Ubuntu 터미널에서 실행
sudo apt update && sudo apt upgrade -y
```

#### 2-2. 필수 패키지 설치

```bash
# 기본 개발 도구
sudo apt install -y \
    git \
    curl \
    wget \
    build-essential \
    libclang-dev \
    clang \
    vim \
    nano \
    unzip \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release
```

#### 2-3. Git 설정

```bash
# Git 사용자 설정
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# 줄바꿈 설정 (Windows 호환)
git config --global core.autocrlf input

# 설정 확인
git config --list
```

---

### 3. Docker Engine 설치 (WSL Ubuntu 내 직접 설치)

#### 3-1. 기존 Docker 패키지 제거 (있는 경우)

```bash
# Ubuntu 터미널에서 실행
sudo apt remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true
```

#### 3-2. Docker 공식 저장소 추가

```bash
# Docker GPG 키 추가
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Docker 저장소 추가
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 패키지 목록 업데이트
sudo apt update
```

#### 3-3. Docker Engine 설치

```bash
# Docker Engine, CLI, Compose 플러그인 설치
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

#### 3-4. Docker 서비스 시작 설정

```bash
# Docker 서비스 시작
sudo service docker start

# WSL 시작 시 Docker 자동 시작 설정
echo '' >> ~/.bashrc
echo '# Docker 자동 시작' >> ~/.bashrc
echo 'if service docker status 2>&1 | grep -q "is not running"; then' >> ~/.bashrc
echo '    sudo service docker start' >> ~/.bashrc
echo 'fi' >> ~/.bashrc
```

#### 3-5. sudo 없이 Docker 사용 설정

```bash
# 현재 사용자를 docker 그룹에 추가
sudo usermod -aG docker $USER

# 그룹 변경 적용 (재로그인 또는 아래 명령 실행)
newgrp docker
```

#### 3-6. sudoers 설정 (Docker 서비스 시작용)

```bash
# sudo 비밀번호 없이 docker 서비스 시작 허용
echo "$USER ALL=(ALL) NOPASSWD: /usr/sbin/service docker start" | sudo tee /etc/sudoers.d/docker-service
```

#### 3-7. Docker 설치 확인

```bash
# 버전 확인
docker --version
# 출력: Docker version 24.x.x, build xxxxx

docker compose version
# 출력: Docker Compose version v2.x.x

# Docker 테스트 (sudo 없이)
docker run hello-world
```

> **참고**: WSL을 새로 열 때마다 Docker 서비스가 자동으로 시작됩니다. 만약 시작되지 않으면 `sudo service docker start`를 실행하세요.

---

### 4. Docker Compose 설치 확인

Docker Desktop에 Docker Compose v2가 포함되어 있습니다.

```bash
# 버전 확인
docker compose version

# 출력 예시:
# Docker Compose version v2.23.0
```

> **참고**: `docker-compose` (하이픈) 명령어도 사용 가능하지만, `docker compose` (공백) 형태가 최신 방식입니다.

---

## Phase 2: 개발 도구 설치

### 5. Python 3.12 설치 및 가상환경 구성

#### 5-1. deadsnakes PPA 추가 및 Python 3.12 설치

```bash
# Ubuntu 터미널에서 실행

# deadsnakes PPA 추가
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update

# Python 3.12 설치
sudo apt install -y python3.12 python3.12-venv python3.12-dev

# pip 설치
curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12

# PATH 설정 (~/.local/bin에 pip이 설치됨)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

#### 5-2. Python 버전 확인

```bash
python3.12 --version
# 출력: Python 3.12.x

python3.12 -m pip --version
# 출력: pip 24.x.x from ...
```

#### 5-3. (선택) Python 3.12를 기본으로 설정

```bash
# update-alternatives 설정
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1
sudo update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1

# 확인
python --version
python3 --version
```

---

### 6. kubectl 설치

```bash
# Ubuntu 터미널에서 실행

# kubectl 바이너리 다운로드
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"

# 설치
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# 다운로드 파일 삭제
rm kubectl

# 버전 확인
kubectl version --client

# 출력 예시:
# Client Version: v1.29.x
```

#### kubectl 자동완성 설정 (선택)

```bash
# bash 자동완성 설치
sudo apt install -y bash-completion

# kubectl 자동완성 활성화
echo 'source <(kubectl completion bash)' >> ~/.bashrc
echo 'alias k=kubectl' >> ~/.bashrc
echo 'complete -o default -F __start_kubectl k' >> ~/.bashrc

# 적용
source ~/.bashrc
```

---

### 7. Minikube 설치

```bash
# Ubuntu 터미널에서 실행

# Minikube 다운로드
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64

# 설치
sudo install minikube-linux-amd64 /usr/local/bin/minikube

# 다운로드 파일 삭제
rm minikube-linux-amd64

# 버전 확인
minikube version

# 출력 예시:
# minikube version: v1.32.x
```

#### Minikube 초기 실행 테스트

```bash
# Docker 드라이버로 Minikube 시작
minikube start --driver=docker --cpus=4 --memory=8192

# 상태 확인
minikube status

# 출력 예시:
# minikube
# type: Control Plane
# host: Running
# kubelet: Running
# apiserver: Running
# kubeconfig: Configured

# 클러스터 정보 확인
kubectl cluster-info
```

---

### 8. Helm 설치

```bash
# Ubuntu 터미널에서 실행

# Helm 설치 스크립트 다운로드 및 실행
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# 버전 확인
helm version

# 출력 예시:
# version.BuildInfo{Version:"v3.14.x", ...}
```

#### Helm 자동완성 설정 (선택)

```bash
echo 'source <(helm completion bash)' >> ~/.bashrc
source ~/.bashrc
```

---

## Phase 3: 프로젝트 설정

### 9. 프로젝트 클론 및 브랜치 체크아웃

#### 9-1. 작업 디렉토리 생성

```bash
# Ubuntu 터미널에서 실행

# 작업 디렉토리 생성 (Windows 경로와 다른 WSL 경로 사용 권장)
mkdir -p ~/projects
cd ~/projects
```

#### 9-2. 프로젝트 클론

```bash
# SSH 방식 (권장)
git clone git@bitbucket.org:mit_dev/generatesdbagent.git

# 또는 HTTPS 방식
git clone https://your-username@bitbucket.org/mit_dev/generatesdbagent.git

# 프로젝트 디렉토리로 이동
cd generatesdbagent
```

#### 9-3. 브랜치 체크아웃

```bash
# 현재 브랜치 확인
git branch -a

# Applying_k8s 브랜치 체크아웃
git checkout Applying_k8s

# 최신 코드 pull
git pull origin Applying_k8s

# 확인
git status
```

#### 9-4. 스크립트 실행 권한 부여

```bash
# scripts 디렉토리의 모든 쉘 스크립트에 실행 권한 부여
chmod +x scripts/*.sh

# 확인
ls -la scripts/
```

#### 9-5. (중요) 줄바꿈 변환 (Windows에서 편집한 경우)

```bash
# dos2unix 설치
sudo apt install -y dos2unix

# 모든 쉘 스크립트 줄바꿈 변환
dos2unix scripts/*.sh
```

---

### 10. .env 파일 생성 및 API 키 설정

#### 10-1. env.example 복사

```bash
cp env.example .env
```

#### 10-2. .env 파일 편집

```bash
nano .env
# 또는
vim .env
```

#### 10-3. 필수 값 입력

```env
# ===== OpenAI 설정 =====
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-4-turbo-preview

# ===== Bitbucket 설정 =====
BITBUCKET_URL=https://api.bitbucket.org
BITBUCKET_USERNAME=your-email@example.com
BITBUCKET_ACCESS_TOKEN=ATCTTxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
BITBUCKET_WORKSPACE=mit_dev
BITBUCKET_REPOSITORY=genw_new

# ===== Router Agent 설정 =====
ROUTER_TIMEOUT=300
CLASSIFICATION_CONFIDENCE_THRESHOLD=0.5
LOG_LEVEL=INFO

# ===== Flask 설정 (SDB Agent) =====
FLASK_ENV=production
TEST_MODE=false
```

#### 10-4. API 키 획득 방법

**OpenAI API Key:**
1. https://platform.openai.com 접속
2. 로그인 -> API Keys 메뉴
3. "Create new secret key" 클릭
4. 생성된 키 복사 (`sk-`로 시작)

**Bitbucket App Password:**
1. Bitbucket 접속 -> 우측 상단 프로필 -> Personal settings
2. 좌측 메뉴 "App passwords" 선택
3. "Create app password" 클릭
4. Label: "GenerateSDBAgent" (또는 원하는 이름)
5. Permissions 선택:
   - Repositories: Read, Write
   - Pull requests: Read, Write
6. "Create" 클릭
7. 생성된 토큰 복사 (`ATCTT`로 시작)

> **주의**: Jira API Token (`ATATT`로 시작)과 Bitbucket App Password (`ATCTT`로 시작)는 다릅니다!

#### 10-5. .env 파일 권한 설정

```bash
# 보안을 위해 읽기 권한 제한
chmod 600 .env
```

---

## Phase 4: 실행 및 검증

### 11. Docker 이미지 빌드

#### 11-1. 이미지 빌드 실행

```bash
# 프로젝트 루트 디렉토리에서 실행
cd ~/projects/generatesdbagent

# Docker 이미지 빌드 (Minikube 없이 로컬 Docker 사용)
USE_MINIKUBE=false ./scripts/build-images.sh

# 또는 직접 빌드
docker build -t router-agent:latest -f router-agent/Dockerfile router-agent/
docker build -t sdb-agent:latest -f sdb-agent/Dockerfile sdb-agent/
```

#### 11-2. 빌드된 이미지 확인

```bash
docker images | grep -E "router-agent|sdb-agent"

# 출력 예시:
# router-agent   latest    xxxxxxxxxxxx   About a minute ago   xxx MB
# sdb-agent      latest    xxxxxxxxxxxx   About a minute ago   xxx MB
```

---

### 12. Docker Compose로 로컬 환경 실행

#### 12-1. Docker Compose 실행

```bash
# 스크립트 사용
./scripts/deploy-local.sh

# 또는 직접 실행
docker compose up -d
```

#### 12-2. 컨테이너 상태 확인

```bash
docker compose ps

# 출력 예시:
# NAME              IMAGE                  COMMAND                  SERVICE         STATUS
# router-agent      router-agent:latest    "uvicorn app.main..."    router-agent    running
# sdb-agent         sdb-agent:latest       "python -m flask..."     sdb-agent       running
# redis             redis:7.2-alpine       "docker-entrypoint..."   redis           running
```

#### 12-3. 로그 확인

```bash
# 모든 서비스 로그
docker compose logs -f

# 특정 서비스 로그
docker compose logs -f router-agent
docker compose logs -f sdb-agent
docker compose logs -f redis
```

---

### 13. 헬스 체크 및 서비스 검증

#### 13-1. 헬스 체크 스크립트 실행

```bash
./scripts/health-check.sh
```

#### 13-2. 수동 헬스 체크

```bash
# Router Agent 헬스 체크
curl http://localhost:5000/health
# 출력: {"status":"healthy","agents":{"sdb":{"status":"healthy",...}}}

# Router Agent - 등록된 에이전트 확인
curl http://localhost:5000/agents
# 출력: {"agents":[{"name":"sdb","description":"...","status":"active"}]}

# Redis 연결 테스트
docker exec redis redis-cli ping
# 출력: PONG
```

#### 13-3. 서비스 중지

```bash
# 서비스 중지 (데이터 유지)
docker compose down

# 서비스 중지 + 볼륨 삭제 (데이터 삭제)
docker compose down -v
```

---

### 14. (선택) Minikube 클러스터 설정 및 Helm 배포

#### 14-1. Minikube 클러스터 설정

```bash
# 기존 Minikube 클러스터 삭제 (필요한 경우)
minikube delete

# Minikube 시작 (Docker 드라이버, 4 CPU, 8GB 메모리)
minikube start --driver=docker --cpus=4 --memory=8192

# 필수 Addons 활성화
minikube addons enable ingress
minikube addons enable metrics-server

# Ingress Controller 준비 대기
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=120s
```

#### 14-2. Minikube Docker 환경에서 이미지 빌드

```bash
# Minikube Docker 환경 사용 설정
eval $(minikube docker-env)

# 이미지 빌드
./scripts/build-images.sh

# 이미지 확인
docker images | grep -E "router-agent|sdb-agent"
```

#### 14-3. Kubernetes Secret 생성

```bash
# 네임스페이스 생성
kubectl create namespace agent-system

# .env 파일에서 Secret 자동 생성
./scripts/create-secrets-from-env.sh --auto

# 또는 수동 생성
kubectl create secret generic agent-secrets \
  --from-literal=openai-api-key='sk-xxxx' \
  --from-literal=bitbucket-access-token='ATCTTxxxx' \
  --from-literal=bitbucket-username='your@email.com' \
  -n agent-system

# Secret 확인
kubectl get secrets -n agent-system
```

#### 14-4. Helm Chart 배포

```bash
# Helm 배포 (로컬 개발 환경)
helm install multi-agent-system ./helm/multi-agent-system \
  -f helm/multi-agent-system/values-local.yaml \
  -n agent-system

# 배포 상태 확인
kubectl get all -n agent-system

# Pod 상태 확인 (모두 Running이 될 때까지 대기)
kubectl get pods -n agent-system -w
```

#### 14-5. Port Forward 설정

```bash
# Router Agent Port Forward (백그라운드)
kubectl port-forward svc/router-agent-svc 5000:5000 -n agent-system &

# 서비스 접근 테스트
curl http://localhost:5000/health
```

#### 14-6. Minikube 대시보드 (선택)

```bash
# 웹 브라우저에서 대시보드 열기
minikube dashboard
```

#### 14-7. Helm 업그레이드/삭제

```bash
# 설정 변경 후 업그레이드
helm upgrade multi-agent-system ./helm/multi-agent-system \
  -f helm/multi-agent-system/values-local.yaml \
  -n agent-system

# 완전 삭제
helm uninstall multi-agent-system -n agent-system
kubectl delete namespace agent-system
```

---

## 추가 설정

### VSCode에서 WSL 사용 (권장)

#### VSCode WSL Extension 설치

1. VSCode 실행
2. Extensions (Ctrl+Shift+X)
3. "WSL" 검색 -> Microsoft 제공 Extension 설치
4. "Remote - WSL" 설치

#### WSL에서 VSCode 실행

```bash
# Ubuntu 터미널에서
cd ~/projects/generatesdbagent
code .
```

---

### 유용한 Alias 설정

```bash
# ~/.bashrc에 추가
cat >> ~/.bashrc << 'EOF'

# Docker aliases
alias d='docker'
alias dc='docker compose'
alias dps='docker ps'
alias dlogs='docker compose logs -f'

# Kubernetes aliases
alias k='kubectl'
alias kgp='kubectl get pods'
alias kgs='kubectl get svc'
alias kga='kubectl get all'
alias kns='kubectl config set-context --current --namespace'

# Project aliases
alias proj='cd ~/projects/generatesdbagent'
alias build='./scripts/build-images.sh'
alias deploy='./scripts/deploy-local.sh'
alias health='./scripts/health-check.sh'
alias logs='./scripts/view-logs.sh'
EOF

# 적용
source ~/.bashrc
```

---

## 트러블슈팅

### 문제 1: Docker 권한 오류

```bash
# 에러: permission denied while trying to connect to the Docker daemon

# 해결: 사용자를 docker 그룹에 추가
sudo usermod -aG docker $USER

# WSL 재시작
wsl --shutdown  # PowerShell에서 실행
# 다시 Ubuntu 터미널 열기
```

### 문제 2: Minikube 시작 실패

```bash
# 에러: Exiting due to DRV_AS_ROOT

# 해결: root가 아닌 일반 사용자로 실행
minikube start --driver=docker --force
```

### 문제 3: 포트 충돌

```bash
# 에러: port 5000 is already in use

# 해결: 사용 중인 포트 확인 및 종료
sudo lsof -i :5000
kill -9 <PID>

# 또는 Docker 컨테이너 모두 정리
docker compose down
docker system prune -f
```

### 문제 4: 이미지 Pull 실패 (Minikube)

```bash
# 에러: ImagePullBackOff

# 해결: Minikube Docker 환경에서 직접 빌드
eval $(minikube docker-env)
./scripts/build-images.sh

# imagePullPolicy: Never 확인 (values-local.yaml)
```

### 문제 5: 스크립트 실행 오류 (줄바꿈 문제)

```bash
# 에러: /bin/bash^M: bad interpreter

# 해결: dos2unix로 줄바꿈 변환
sudo apt install -y dos2unix
dos2unix scripts/*.sh
```

### 문제 6: Secret 관련 오류

```bash
# 에러: secret "agent-secrets" not found

# 해결: Secret 재생성
kubectl delete secret agent-secrets -n agent-system --ignore-not-found
./scripts/create-secrets-from-env.sh --auto
```

---

## 전체 명령어 요약 (복사용)

```bash
# === Phase 1: Ubuntu 기본 설정 ===
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl wget build-essential libclang-dev clang vim nano unzip software-properties-common apt-transport-https ca-certificates gnupg lsb-release dos2unix

# === Phase 2: 개발 도구 설치 ===
# Python 3.12
sudo add-apt-repository ppa:deadsnakes/ppa -y && sudo apt update
sudo apt install -y python3.12 python3.12-venv python3.12-dev
curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12

# kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl && rm kubectl

# Minikube
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube && rm minikube-linux-amd64

# Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# === Phase 3: 프로젝트 설정 ===
mkdir -p ~/projects && cd ~/projects
git clone <repository-url>
cd generatesdbagent
git checkout Applying_k8s
chmod +x scripts/*.sh
dos2unix scripts/*.sh
cp env.example .env
nano .env  # API 키 입력

# === Phase 4: 실행 ===
USE_MINIKUBE=false ./scripts/build-images.sh
./scripts/deploy-local.sh
./scripts/health-check.sh
```

---

## 예상 소요 시간

| Phase | 작업 | 소요 시간 |
|-------|------|----------|
| Phase 1 | WSL2 + Docker Desktop | ~30분 |
| Phase 2 | 개발 도구 설치 | ~20분 |
| Phase 3 | 프로젝트 설정 | ~10분 |
| Phase 4 | 실행 및 검증 | ~15분 |
| **총합** | | **약 1시간 ~ 1시간 30분** |

---

## 관련 문서

- [QUICKSTART.md](./QUICKSTART.md) - 빠른 시작 가이드
- [README.md](./README.md) - 프로젝트 개요
- [scripts/README.md](./scripts/README.md) - 스크립트 상세 가이드
- [docs/kubernetes/](./docs/kubernetes/) - Kubernetes 배포 가이드
- [docs/redis/](./docs/redis/) - Redis 설정 가이드
