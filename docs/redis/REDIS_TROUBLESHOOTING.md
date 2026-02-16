# Redis 캐싱 트러블슈팅 가이드

## 목차
1. [일반적인 문제](#일반적인-문제)
2. [DNS 이름 해석 실패](#dns-이름-해석-실패)
3. [환경 변수 설정 문제](#환경-변수-설정-문제)
4. [Helm 배포 문제](#helm-배포-문제)
5. [디버깅 도구](#디버깅-도구)

---

## 일반적인 문제

### 증상: Redis 연결 실패

**에러 메시지:**
```
Redis 연결 실패: Error -3 connecting to redis:6379. Temporary failure in name resolution.
```

**원인:** Kubernetes DNS가 "redis" 호스트를 찾을 수 없음

**해결 순서:**
1. [Redis Service 확인](#1-redis-service-확인)
2. [환경 변수 확인](#2-환경-변수-확인)
3. [DNS 해석 테스트](#3-dns-해석-테스트)
4. [Helm 배포 상태 확인](#4-helm-배포-상태-확인)

---

## DNS 이름 해석 실패

### 1. Redis Service 확인

**증상:**
```bash
Error -3 connecting to redis:6379. Temporary failure in name resolution.
```

**진단:**
```bash
# Redis Service 존재 여부 확인
kubectl get svc redis -n agent-system
```

**예상 출력:**
```
# ✅ 정상
NAME    TYPE        CLUSTER-IP       EXTERNAL-IP   PORT(S)    AGE
redis   ClusterIP   10.106.234.149   <none>        6379/TCP   27h

# ❌ 문제
Error from server (NotFound): services "redis" not found
```

**해결:**
```bash
# Redis Service가 없다면 Helm upgrade
helm upgrade multi-agent-system ./helm/multi-agent-system -n agent-system

# Redis Service 생성 확인
kubectl get svc redis -n agent-system
```

---

### 2. 환경 변수 확인

**진단:**
```bash
# Router Agent Pod의 환경 변수 확인
kubectl get pod -n agent-system -l app=router-agent -o yaml | grep -A 3 "REDIS_HOST"
```

**예상 출력:**
```yaml
# ✅ 정상 - values.yaml에서 주입됨
- name: REDIS_HOST
  value: "redis"
- name: REDIS_PORT
  value: "6379"
- name: REDIS_DB
  value: "0"

# ❌ 문제 - 환경 변수 없음
# (출력 없음)
```

**해결:**
```bash
# values.yaml에 global.redis 설정이 있는지 확인
grep -A 5 "global:" helm/multi-agent-system/values.yaml

# Helm upgrade 실행
helm upgrade multi-agent-system ./helm/multi-agent-system -n agent-system

# Pod 재시작 확인
kubectl rollout status deployment/router-agent -n agent-system
```

---

### 3. DNS 해석 테스트

**진단:**
```bash
# Router Agent Pod 이름 가져오기
ROUTER_POD=$(kubectl get pod -n agent-system -l app=router-agent -o jsonpath='{.items[0].metadata.name}')

# DNS 해석 테스트
kubectl exec -it $ROUTER_POD -n agent-system -- nslookup redis
```

**예상 출력:**
```
# ✅ 정상
Server:    10.96.0.10
Address:   10.96.0.10:53

Name:      redis.agent-system.svc.cluster.local
Address:   10.106.234.149

# ❌ 문제
Server:    10.96.0.10
Address:   10.96.0.10:53

** server can't find redis: NXDOMAIN
```

**해결:**
```bash
# CoreDNS 상태 확인
kubectl get pods -n kube-system | grep coredns

# CoreDNS 재시작 (필요 시)
kubectl rollout restart deployment/coredns -n kube-system
```

---

### 4. Helm 배포 상태 확인

**진단:**
```bash
# Helm 릴리스 확인
helm list -n agent-system

# 배포된 리소스 확인
kubectl get all -n agent-system
```

**예상 출력:**
```
# ✅ 정상
NAME                    REVISION    STATUS      CHART                       NAMESPACE
multi-agent-system      4           deployed    multi-agent-system-1.0.0    agent-system
```

**해결:**
```bash
# Helm upgrade 실행
helm upgrade multi-agent-system ./helm/multi-agent-system -n agent-system

# 배포 상태 확인
kubectl get pods -n agent-system -w
```

---

## 환경 변수 설정 문제

### 증상: 코드 기본값(localhost) 사용됨

**에러 메시지:**
```
Redis 연결 실패: Error connecting to localhost:6379
```

**원인:** 환경 변수가 Pod에 주입되지 않아 코드의 기본값 사용

**진단:**
```bash
# Pod 안에서 환경 변수 확인
kubectl exec -it $ROUTER_POD -n agent-system -- env | grep REDIS

# 예상 출력 (정상):
# REDIS_HOST=redis
# REDIS_PORT=6379
# REDIS_DB=0

# 예상 출력 (문제):
# (출력 없음)
```

**해결:**

1. **values.yaml 확인:**
   ```yaml
   # helm/multi-agent-system/values.yaml
   global:
     redis:
       host: "redis"
       port: 6379
       db: 0
   ```

2. **Deployment 템플릿 확인:**
   ```yaml
   # templates/router-agent/deployment.yaml
   env:
     - name: REDIS_HOST
       value: {{ .Values.global.redis.host | quote }}
   ```

3. **Helm upgrade 실행:**
   ```bash
   helm upgrade multi-agent-system ./helm/multi-agent-system -n agent-system
   kubectl rollout status deployment/router-agent -n agent-system
   ```

---

## Helm 배포 문제

### 증상: 설정 변경이 반영되지 않음

**원인:** Helm upgrade를 실행하지 않음

**해결 체크리스트:**

```bash
# ✅ 1. values.yaml 수정했는가?
vim helm/multi-agent-system/values.yaml

# ✅ 2. Helm upgrade 실행했는가?
helm upgrade multi-agent-system ./helm/multi-agent-system -n agent-system

# ✅ 3. Pod가 재시작되었는가?
kubectl get pods -n agent-system
# AGE가 최근으로 변경되었는지 확인

# ✅ 4. 환경 변수가 변경되었는가?
kubectl describe pod -n agent-system -l app=router-agent | grep -A 5 "Environment:"
```

---

### 증상: 코드 변경이 반영되지 않음

**원인:** Docker 이미지를 재빌드하지 않음

**해결:**

```bash
# 1. Docker 이미지 재빌드
cd router-agent
docker build -t router-agent:1.0.0 .

# 2. Minikube에 이미지 로드
minikube image load router-agent:1.0.0

# 3. Pod 재시작
kubectl rollout restart deployment/router-agent -n agent-system

# 4. 재시작 완료 대기
kubectl rollout status deployment/router-agent -n agent-system
```

---

## 디버깅 도구

### 로그 확인

```bash
# 최근 50줄의 로그 확인
kubectl logs -n agent-system -l app=router-agent --tail=50

# Redis 관련 로그만 필터링
kubectl logs -n agent-system -l app=router-agent --tail=100 | grep -i redis

# 실시간 로그 스트리밍
kubectl logs -n agent-system -l app=router-agent -f
```

### Pod 내부 접속

```bash
# Pod 안으로 들어가기
ROUTER_POD=$(kubectl get pod -n agent-system -l app=router-agent -o jsonpath='{.items[0].metadata.name}')
kubectl exec -it $ROUTER_POD -n agent-system -- sh

# Pod 안에서 테스트
nslookup redis
nc -zv redis 6379
env | grep REDIS
```

### Redis 직접 테스트

```bash
# Redis Pod 안으로 들어가기
REDIS_POD=$(kubectl get pod -n agent-system -l app=redis -o jsonpath='{.items[0].metadata.name}')
kubectl exec -it $REDIS_POD -n agent-system -- sh

# Redis CLI 테스트
redis-cli ping
# PONG

redis-cli
> SET test "hello"
> GET test
> KEYS *
> EXIT
```

### 캐싱 테스트

```bash
# 공식 테스트 스크립트 실행
bash scripts/test-redis-caching.sh

# Router Agent 캐시 통계 확인
curl http://localhost:8080/metrics | grep cache
```

---

## 빠른 체크리스트

문제 발생 시 다음 순서로 확인:

```bash
# 1. Redis Service 확인
kubectl get svc redis -n agent-system

# 2. Redis Pod 확인
kubectl get pod -n agent-system | grep redis

# 3. Router Agent Pod 확인
kubectl get pod -n agent-system -l app=router-agent

# 4. 환경 변수 확인
kubectl describe pod -n agent-system -l app=router-agent | grep -A 5 "REDIS_HOST"

# 5. 로그 확인
kubectl logs -n agent-system -l app=router-agent --tail=20 | grep -i redis

# 6. DNS 테스트
ROUTER_POD=$(kubectl get pod -n agent-system -l app=router-agent -o jsonpath='{.items[0].metadata.name}')
kubectl exec -it $ROUTER_POD -n agent-system -- nslookup redis

# 7. Helm 상태 확인
helm list -n agent-system
```

---

## 일반적인 해결 패턴

### 패턴 1: 설정만 변경 (values.yaml)

```bash
# 설정 변경
vim helm/multi-agent-system/values.yaml

# Helm upgrade
helm upgrade multi-agent-system ./helm/multi-agent-system -n agent-system

# 완료 대기
kubectl rollout status deployment/router-agent -n agent-system
```

### 패턴 2: 코드 변경 (Python 파일)

```bash
# 코드 변경
vim router-agent/app/main.py

# Docker 이미지 재빌드
cd router-agent
docker build -t router-agent:1.0.0 .

# Minikube에 로드
minikube image load router-agent:1.0.0

# Pod 재시작
kubectl rollout restart deployment/router-agent -n agent-system
```

### 패턴 3: 완전 재배포

```bash
# 기존 배포 삭제
helm uninstall multi-agent-system -n agent-system

# 새로 배포
helm install multi-agent-system ./helm/multi-agent-system -n agent-system

# 상태 확인
kubectl get all -n agent-system
```

---

## 추가 리소스

- [Redis 연결 원리](./REDIS_CONNECTION.md)
- [설정 관리 가이드](./CONFIGURATION_MANAGEMENT.md)
- [배포 워크플로우](./DEPLOYMENT_WORKFLOW.md)
