# Kubernetes 배포 워크플로우 가이드

## 목차
1. [Docker와 Kubernetes 관계](#docker와-kubernetes-관계)
2. [시나리오별 워크플로우](#시나리오별-워크플로우)
3. [Docker 관리](#docker-관리)
4. [개발 워크플로우](#개발-워크플로우)
5. [모범 사례](#모범-사례)

---

## Docker와 Kubernetes 관계

### 전체 구조

```
Docker Desktop
    ↓ (Docker daemon 제공)
Minikube
    ↓ (Kubernetes 클러스터)
Helm으로 배포된 애플리케이션
```

### 각 구성 요소의 역할

#### Docker Desktop
- **역할:** Docker 이미지 빌드 및 관리
- **필요한 경우:**
  - ✅ Minikube 실행 (Minikube가 Docker 드라이버 사용 시)
  - ✅ Docker 이미지 빌드
  - ❌ 테스트하지 않을 때 (종료 가능)

#### Minikube
- **역할:** 로컬 Kubernetes 클러스터 제공
- **필요한 경우:**
  - ✅ 애플리케이션 배포 및 테스트
  - ✅ Kubernetes 리소스 관리

#### Helm
- **역할:** Kubernetes 패키지 관리자
- **필요한 경우:**
  - ✅ 애플리케이션 배포
  - ✅ 설정 변경 및 업그레이드

---

## 시나리오별 워크플로우

### 시나리오 1: values.yaml만 수정 (설정 변경)

**수정 내용:**
- Redis 포트 변경
- 리소스 제한 변경
- 환경 변수 변경

**워크플로우:**
```bash
# 1. values.yaml 수정
vim helm/multi-agent-system/values.yaml

# 예: Redis 포트 변경
global:
  redis:
    host: "redis"
    port: 6380  # 6379 → 6380

# 2. Helm upgrade (Docker 빌드 불필요!)
helm upgrade multi-agent-system ./helm/multi-agent-system -n agent-system

# 3. 변경사항 적용 대기
kubectl rollout status deployment/router-agent -n agent-system

# 4. 확인
kubectl logs -n agent-system -l app=router-agent --tail=10 | grep -i redis
```

**Docker 이미지 재빌드:** ❌ **불필요**

**시간:** ~30초

---

### 시나리오 2: Python 코드 수정 (로직 변경)

**수정 내용:**
- `router-agent/app/main.py` 수정
- 새로운 기능 추가
- 버그 수정

**워크플로우:**
```bash
# 1. 코드 수정
vim router-agent/app/main.py

# 2. Docker 이미지 재빌드 (필수!)
cd router-agent
docker build -t router-agent:1.0.1 .  # 버전 올리기 권장

# 3. Minikube에 이미지 로드
minikube image load router-agent:1.0.1

# 4. values.yaml에서 이미지 태그 변경
vim ../helm/multi-agent-system/values.yaml
# routerAgent:
#   image:
#     tag: "1.0.1"

# 5. Helm upgrade
cd ..
helm upgrade multi-agent-system ./helm/multi-agent-system -n agent-system

# 6. Pod 재시작 확인
kubectl rollout status deployment/router-agent -n agent-system

# 7. 확인
kubectl logs -n agent-system -l app=router-agent --tail=20
```

**Docker 이미지 재빌드:** ✅ **필수**

**시간:** ~2-3분 (이미지 빌드 시간 포함)

---

### 시나리오 3: Helm 템플릿 수정

**수정 내용:**
- `templates/router-agent/deployment.yaml` 수정
- 새로운 ConfigMap 추가
- 리소스 정의 변경

**워크플로우:**
```bash
# 1. 템플릿 수정
vim helm/multi-agent-system/templates/router-agent/deployment.yaml

# 2. Helm upgrade
helm upgrade multi-agent-system ./helm/multi-agent-system -n agent-system

# 3. 변경사항 확인
kubectl get deployment router-agent -n agent-system -o yaml
```

**Docker 이미지 재빌드:** ❌ **불필요**

**시간:** ~30초

---

### 시나리오 4: 완전 재배포

**필요한 경우:**
- 심각한 문제 발생
- 깨끗한 상태로 시작
- 대규모 변경

**워크플로우:**
```bash
# 1. 기존 배포 삭제
helm uninstall multi-agent-system -n agent-system

# 2. PVC 삭제 (데이터 초기화 필요 시)
kubectl delete pvc --all -n agent-system

# 3. Docker 이미지 재빌드 (코드 변경 시)
cd router-agent
docker build -t router-agent:1.0.0 .
cd ../sdb-agent
docker build -t sdb-agent:1.0.0 .
cd ..

# 4. Minikube에 이미지 로드
minikube image load router-agent:1.0.0
minikube image load sdb-agent:1.0.0

# 5. Secret 재생성 (삭제되었으므로)
kubectl create secret generic agent-secrets \
  --from-literal=openai-api-key='your-key' \
  --from-literal=bitbucket-access-token='your-token' \
  --from-literal=bitbucket-username='your-username' \
  -n agent-system

# 6. 새로 배포
helm install multi-agent-system ./helm/multi-agent-system -n agent-system

# 7. 모든 Pod Running 대기
kubectl get pods -n agent-system -w

# 8. 상태 확인
kubectl get all -n agent-system
```

**시간:** ~5분

---

## Docker 관리

### Docker Desktop 종료 가능 여부

#### 완전히 종료 가능한 경우

```bash
# 모든 리소스 정리
minikube stop

# 이후 Docker Desktop 종료 가능
```

**주의:**
- Docker Desktop 종료 시 **Minikube도 멈춤**
- 다음 작업 시 재시작 필요

#### 다시 시작하는 방법

```bash
# 1. Docker Desktop 실행

# 2. Minikube 시작
minikube start

# 3. Pod 상태 확인
kubectl get pods -n agent-system

# 모든 Pod가 Running이 될 때까지 대기
```

---

### 리소스 관리 옵션

#### 옵션 1: 항상 실행 (편리함 우선)

**장점:**
- 즉시 테스트 가능
- 재시작 시간 불필요

**단점:**
- 메모리 4-8GB 사용
- CPU 리소스 소비

**권장 대상:**
- 하루 종일 개발하는 경우
- 리소스가 충분한 경우

```bash
# Docker Desktop 계속 실행
# Minikube 계속 실행
```

---

#### 옵션 2: 필요할 때만 실행 (리소스 절약)

**장점:**
- 리소스 절약
- 배터리 절약 (노트북)

**단점:**
- 시작 시간 필요 (~1-2분)

**권장 대상:**
- 가끔 테스트하는 경우
- 리소스가 제한적인 경우

```bash
# 개발/테스트 시작
minikube start

# 개발/테스트 종료
minikube stop
# Docker Desktop 종료
```

---

#### 옵션 3: 일시 정지 (빠른 재개)

**장점:**
- 빠른 재개 (~10초)
- 상태 유지

**단점:**
- 메모리는 계속 사용

**권장 대상:**
- 잠깐 쉬는 동안
- 점심 시간

```bash
# 일시 정지
minikube pause

# 재개
minikube unpause

# 확인
kubectl get pods -n agent-system
```

---

## 개발 워크플로우

### 일상 개발 워크플로우

#### 아침 (개발 환경 시작)

```bash
# 1. Docker Desktop 실행 (GUI)

# 2. Minikube 시작
minikube start

# 3. 상태 확인
kubectl get pods -n agent-system

# 4. Port Forward 시작 (필요 시)
kubectl port-forward -n agent-system svc/router-agent-svc 8080:5000 &
```

---

#### 개발 중 (코드 수정)

**설정만 변경:**
```bash
# values.yaml 수정
vim helm/multi-agent-system/values.yaml

# Helm upgrade
helm upgrade multi-agent-system ./helm/multi-agent-system -n agent-system

# 로그 확인
kubectl logs -n agent-system -l app=router-agent --tail=20
```

**코드 변경:**
```bash
# 코드 수정
vim router-agent/app/main.py

# Docker 이미지 재빌드
cd router-agent
docker build -t router-agent:1.0.0 .

# Minikube에 로드
minikube image load router-agent:1.0.0

# Pod 재시작
kubectl rollout restart deployment/router-agent -n agent-system

# 로그 확인
kubectl logs -n agent-system -l app=router-agent --tail=20 -f
```

---

#### 테스트

```bash
# 캐싱 테스트
bash scripts/test-redis-caching.sh

# 수동 테스트
curl -X POST http://localhost:8080/process \
  -H "Content-Type: application/json" \
  -d '{"issue_key": "TEST-123", "summary": "Test issue"}'

# 로그 확인
kubectl logs -n agent-system -l app=router-agent -f
```

---

#### 퇴근 (환경 정리)

**옵션 A: 모두 종료 (리소스 절약)**
```bash
# Minikube 종료
minikube stop

# Docker Desktop 종료 (GUI)
```

**옵션 B: 유지 (다음날 빠른 시작)**
```bash
# Minikube pause
minikube pause

# Docker Desktop은 실행 상태 유지
```

---

### 빠른 참조

#### 코드 수정 후 배포 체크리스트

```bash
# ✅ 1. 코드 수정
# router-agent/app/main.py 등

# ✅ 2. Docker 이미지 빌드
cd router-agent
docker build -t router-agent:1.0.0 .

# ✅ 3. Minikube에 로드
minikube image load router-agent:1.0.0

# ✅ 4. Pod 재시작 (두 가지 방법 중 선택)

# 방법 A: Helm upgrade (권장)
helm upgrade multi-agent-system ./helm/multi-agent-system -n agent-system

# 방법 B: 직접 재시작 (빠름)
kubectl rollout restart deployment/router-agent -n agent-system

# ✅ 5. 상태 확인
kubectl rollout status deployment/router-agent -n agent-system
kubectl logs -n agent-system -l app=router-agent --tail=20

# ✅ 6. 테스트
bash scripts/test-redis-caching.sh
```

---

## 모범 사례

### 1. 버전 관리

**이미지 태그에 버전 사용:**
```bash
# ✅ 권장
docker build -t router-agent:1.0.1 .
docker build -t router-agent:1.0.2 .

# ❌ 비권장
docker build -t router-agent:latest .
```

**이유:**
- 롤백 가능
- 버전 추적 용이
- 캐시 문제 방지

---

### 2. Helm Upgrade vs Rollout Restart

**Helm upgrade 사용 (권장):**
```bash
helm upgrade multi-agent-system ./helm/multi-agent-system -n agent-system
```

**장점:**
- values.yaml 변경사항 반영
- 전체 상태 동기화
- Git 히스토리와 일치

**Rollout restart 사용:**
```bash
kubectl rollout restart deployment/router-agent -n agent-system
```

**장점:**
- 빠름 (~10초)
- 간단

**사용 시기:**
- 이미지만 재로드
- 빠른 테스트

---

### 3. 로그 확인 습관

**배포 후 항상 로그 확인:**
```bash
# 배포 후
kubectl logs -n agent-system -l app=router-agent --tail=20

# 에러 찾기
kubectl logs -n agent-system -l app=router-agent --tail=100 | grep -i error

# 실시간 모니터링
kubectl logs -n agent-system -l app=router-agent -f
```

---

### 4. 환경 분리

**개발 환경:**
```bash
helm upgrade multi-agent-system ./helm/multi-agent-system \
  -n agent-system \
  -f helm/multi-agent-system/values-dev.yaml
```

**프로덕션 환경:**
```bash
helm upgrade multi-agent-system ./helm/multi-agent-system \
  -n production \
  -f helm/multi-agent-system/values-production.yaml
```

---

### 5. Git 커밋 전 테스트

```bash
# 1. 변경사항 적용
helm upgrade multi-agent-system ./helm/multi-agent-system -n agent-system

# 2. 테스트
bash scripts/test-redis-caching.sh

# 3. 로그 확인
kubectl logs -n agent-system -l app=router-agent --tail=50

# 4. 성공하면 커밋
git add .
git commit -m "feat: Add Redis caching"
git push
```

---

## 문제 해결

### Pod가 재시작되지 않음

**진단:**
```bash
kubectl get pods -n agent-system
# AGE 확인
```

**해결:**
```bash
# 수동 재시작
kubectl rollout restart deployment/router-agent -n agent-system
```

---

### 이미지 변경이 반영되지 않음

**원인:** Kubernetes가 이전 이미지 사용

**해결:**
```bash
# 1. 이미지 태그 변경
# values.yaml:
# routerAgent.image.tag: "1.0.1"  # 1.0.0 → 1.0.1

# 2. Helm upgrade
helm upgrade multi-agent-system ./helm/multi-agent-system -n agent-system

# 또는 imagePullPolicy 변경
# values.yaml:
# imageRegistry.pullPolicy: Always  # IfNotPresent → Always
```

---

### Minikube가 느림

**해결:**
```bash
# 리소스 증가
minikube delete
minikube start --cpus=4 --memory=8192

# 드라이버 변경 (macOS/Linux)
minikube start --driver=docker
minikube start --driver=hyperkit  # macOS
minikube start --driver=kvm2      # Linux
```

---

## 유용한 명령어

### 전체 상태 확인

```bash
# 모든 리소스
kubectl get all -n agent-system

# Pod 상세 정보
kubectl describe pod -n agent-system -l app=router-agent

# 이벤트 확인
kubectl get events -n agent-system --sort-by='.lastTimestamp'
```

### 리소스 정리

```bash
# Pod 로그 삭제 (재시작)
kubectl delete pod -n agent-system -l app=router-agent

# 모든 리소스 삭제
helm uninstall multi-agent-system -n agent-system

# Namespace 삭제 (완전 정리)
kubectl delete namespace agent-system
```

---

## 참고 자료

- [Redis 연결 원리](./REDIS_CONNECTION.md)
- [설정 관리](./CONFIGURATION_MANAGEMENT.md)
- [트러블슈팅 가이드](./REDIS_TROUBLESHOOTING.md)
