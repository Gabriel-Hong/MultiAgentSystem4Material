# Redis 캐싱 시스템 문서

Multi-Agent 시스템의 Redis 캐싱 구현, 배포, 관리에 대한 종합 가이드입니다.

## 📚 문서 목록

### 1. [Redis 연결 원리](./REDIS_CONNECTION.md)
Redis가 Kubernetes에 어떻게 배포되고 애플리케이션과 연결되는지에 대한 상세 설명

**주요 내용:**
- Redis 배포 구조 (Deployment, Service, ConfigMap, PVC)
- Helm을 통한 배포 과정
- Kubernetes DNS 작동 원리
- 환경 변수 주입 메커니즘
- 전체 연결 흐름 다이어그램

**대상:**
- Kubernetes DNS가 어떻게 작동하는지 이해하고 싶은 개발자
- Redis가 "redis"라는 이름만으로 연결되는 원리를 알고 싶은 분
- Helm 템플릿이 어떻게 렌더링되는지 궁금한 분

---

### 2. [설정 관리 가이드](./CONFIGURATION_MANAGEMENT.md)
Redis 설정을 Single Source of Truth로 관리하는 방법과 환경별 설정 관리

**주요 내용:**
- values.yaml을 유일한 설정 소스로 사용
- 환경별 설정 분리 (dev/staging/production)
- 환경 변수 우선순위
- 민감 정보 관리 (Secret)
- 설정 검증 방법

**대상:**
- 설정이 여러 곳에 중복되어 관리가 어려운 분
- 환경별로 다른 설정을 사용하고 싶은 분
- 환경 변수가 어떤 우선순위로 적용되는지 알고 싶은 분

---

### 3. [트러블슈팅 가이드](./REDIS_TROUBLESHOOTING.md)
Redis 연결 문제 진단 및 해결 방법

**주요 내용:**
- DNS 이름 해석 실패 문제
- 환경 변수 설정 문제
- Helm 배포 문제
- 디버깅 도구 및 명령어
- 빠른 체크리스트

**대상:**
- "Temporary failure in name resolution" 에러를 만난 분
- Redis 연결이 실패하는 분
- Helm upgrade 후 설정이 반영되지 않는 분

---

### 4. [배포 워크플로우](./DEPLOYMENT_WORKFLOW.md)
Kubernetes 환경에서 개발, 배포, 테스트하는 실무 워크플로우

**주요 내용:**
- Docker와 Kubernetes 관계
- 시나리오별 워크플로우 (코드 수정, 설정 변경, 완전 재배포)
- Docker Desktop 관리 (언제 켜고 끄는가)
- 일상 개발 워크플로우
- 모범 사례

**대상:**
- Kubernetes 개발 워크플로우가 처음인 분
- Docker 이미지를 언제 재빌드해야 하는지 헷갈리는 분
- Docker Desktop을 항상 켜놔야 하는지 궁금한 분

---

## 🚀 빠른 시작

### Redis가 연결되지 않을 때

```bash
# 1. Redis Service 확인
kubectl get svc redis -n agent-system

# 2. 환경 변수 확인
kubectl describe pod -n agent-system -l app=router-agent | grep -A 3 "REDIS_HOST"

# 3. DNS 테스트
ROUTER_POD=$(kubectl get pod -n agent-system -l app=router-agent -o jsonpath='{.items[0].metadata.name}')
kubectl exec -it $ROUTER_POD -n agent-system -- nslookup redis

# 4. Helm upgrade
helm upgrade multi-agent-system ./helm/multi-agent-system -n agent-system
```

자세한 내용은 [트러블슈팅 가이드](./REDIS_TROUBLESHOOTING.md)를 참고하세요.

---

### 코드 변경 후 배포

```bash
# 1. 코드 수정
vim router-agent/app/main.py

# 2. Docker 이미지 재빌드
cd router-agent && docker build -t router-agent:1.0.0 .

# 3. Minikube에 로드
minikube image load router-agent:1.0.0

# 4. Pod 재시작
kubectl rollout restart deployment/router-agent -n agent-system

# 5. 확인
kubectl logs -n agent-system -l app=router-agent --tail=20
```

자세한 내용은 [배포 워크플로우](./DEPLOYMENT_WORKFLOW.md)를 참고하세요.

---

### 설정 변경

```bash
# 1. values.yaml 수정
vim helm/multi-agent-system/values.yaml

# 예: Redis 호스트 변경
global:
  redis:
    host: "my-redis"
    port: 6380

# 2. Helm upgrade (Docker 빌드 불필요!)
helm upgrade multi-agent-system ./helm/multi-agent-system -n agent-system

# 3. 확인
kubectl logs -n agent-system -l app=router-agent --tail=10 | grep -i redis
```

자세한 내용은 [설정 관리 가이드](./CONFIGURATION_MANAGEMENT.md)를 참고하세요.

---

## 📖 학습 경로

### 초급: Kubernetes가 처음이라면

1. **[Redis 연결 원리](./REDIS_CONNECTION.md)** 먼저 읽기
   - Kubernetes DNS 이해
   - Service와 Pod의 관계
   - 환경 변수 주입 방식

2. **[배포 워크플로우](./DEPLOYMENT_WORKFLOW.md)** 실습
   - Minikube 시작하기
   - 간단한 설정 변경해보기
   - 로그 확인하기

### 중급: 개발 중 문제를 만난다면

1. **[트러블슈팅 가이드](./REDIS_TROUBLESHOOTING.md)** 참고
   - 에러 메시지로 원인 찾기
   - 빠른 체크리스트 실행
   - 디버깅 도구 활용

2. **[설정 관리 가이드](./CONFIGURATION_MANAGEMENT.md)** 숙지
   - 환경 변수 우선순위 이해
   - values.yaml 제대로 사용하기

### 고급: 프로덕션 배포 준비

1. **[설정 관리 가이드](./CONFIGURATION_MANAGEMENT.md)** 심화
   - 환경별 설정 분리
   - Secret으로 민감 정보 관리
   - 모범 사례 적용

2. **[배포 워크플로우](./DEPLOYMENT_WORKFLOW.md)** 최적화
   - 버전 관리 전략
   - CI/CD 파이프라인 구축

---

## 🔧 유용한 명령어 모음

### 상태 확인
```bash
# 전체 리소스
kubectl get all -n agent-system

# Redis 연결 확인
kubectl logs -n agent-system -l app=router-agent --tail=20 | grep -i redis

# 환경 변수 확인
kubectl describe pod -n agent-system -l app=router-agent | grep -A 5 "Environment:"
```

### 문제 해결
```bash
# DNS 테스트
kubectl exec -it <pod-name> -n agent-system -- nslookup redis

# Redis 직접 테스트
kubectl exec -it <redis-pod> -n agent-system -- redis-cli ping

# 로그 스트리밍
kubectl logs -n agent-system -l app=router-agent -f
```

### 배포
```bash
# Helm upgrade
helm upgrade multi-agent-system ./helm/multi-agent-system -n agent-system

# Pod 재시작
kubectl rollout restart deployment/router-agent -n agent-system

# 완전 재배포
helm uninstall multi-agent-system -n agent-system
helm install multi-agent-system ./helm/multi-agent-system -n agent-system
```

---

## 📌 핵심 개념 요약

### Redis 배포
- ✅ Helm Chart로 Redis Deployment, Service, ConfigMap, PVC 생성
- ✅ Service 이름 "redis"가 DNS 이름이 됨
- ✅ values.yaml이 Single Source of Truth

### Redis 연결
- ✅ Kubernetes DNS(CoreDNS)가 "redis" → IP 변환
- ✅ 환경 변수로 호스트 정보 주입 (values.yaml → Pod)
- ✅ Python 코드는 환경 변수 우선 사용

### 배포 워크플로우
- ✅ 설정 변경: Helm upgrade만
- ✅ 코드 변경: Docker 재빌드 + Minikube 로드 + Pod 재시작
- ✅ 템플릿 변경: Helm upgrade만

---

## 🤝 기여

문서에 오류나 개선사항이 있다면 이슈를 생성해주세요.

---

## 📚 추가 리소스

### 공식 문서
- [Kubernetes DNS](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/)
- [Helm 공식 문서](https://helm.sh/docs/)
- [Redis 공식 문서](https://redis.io/docs/)

### 프로젝트 관련
- [전체 시스템 아키텍처](../../README.md)
- [Monitoring 가이드](../monitoring/)
- [Multi-Agent 시스템 가이드](../../sdb-agent/doc/MULTI_AGENT_ARCHITECTURE.md)

---

**마지막 업데이트:** 2025-11-04
