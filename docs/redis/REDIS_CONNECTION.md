# Redis 연결 원리

## 목차
1. [Redis 배포 구조](#redis-배포-구조)
2. [Helm을 통한 배포](#helm을-통한-배포)
3. [Kubernetes DNS 작동 원리](#kubernetes-dns-작동-원리)
4. [환경 변수 주입](#환경-변수-주입)
5. [전체 연결 흐름](#전체-연결-흐름)

---

## Redis 배포 구조

### Kubernetes 리소스

Redis는 다음 4개의 Kubernetes 리소스로 구성됩니다:

```
helm/multi-agent-system/templates/redis/
├── deployment.yaml    # Redis Pod 정의
├── service.yaml       # Redis Service (DNS 이름 제공)
├── configmap.yaml     # Redis 설정 파일
└── pvc.yaml          # 데이터 영구 저장
```

### 각 리소스의 역할

#### 1. Deployment (Redis Pod)
```yaml
# templates/redis/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: agent-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    spec:
      containers:
        - name: redis
          image: redis:7.2-alpine
          ports:
            - containerPort: 6379
              name: redis
```

**역할:**
- Redis 서버 프로세스 실행
- 포트 6379로 요청 수신
- ConfigMap의 설정 파일 사용

---

#### 2. Service (DNS 이름 제공)
```yaml
# templates/redis/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: redis                    # ← 이것이 DNS 이름!
  namespace: agent-system
spec:
  type: ClusterIP
  ports:
    - port: 6379
      targetPort: 6379
  selector:
    app: redis                   # ← 이 라벨을 가진 Pod와 연결
```

**역할:**
- DNS 이름 "redis" 제공
- ClusterIP (가상 IP) 할당
- Pod로 트래픽 라우팅

---

#### 3. ConfigMap (Redis 설정)
```yaml
# templates/redis/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: redis-config
data:
  redis.conf: |
    bind 0.0.0.0
    protected-mode no
    port 6379
    maxmemory 512mb
    maxmemory-policy allkeys-lru
```

**역할:**
- Redis 서버 설정
- 메모리 제한 및 정책
- 네트워크 설정

---

#### 4. PersistentVolumeClaim (데이터 저장)
```yaml
# templates/redis/pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: redis-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
```

**역할:**
- Redis 데이터 영구 저장
- Pod 재시작 시에도 데이터 유지

---

## Helm을 통한 배포

### Helm Chart 구조

```
helm/multi-agent-system/
├── Chart.yaml           # Chart 메타데이터
├── values.yaml          # 설정 값 (Single Source of Truth)
└── templates/           # Kubernetes 리소스 템플릿
    ├── redis/
    ├── router-agent/
    └── sdb-agent/
```

### Helm 배포 과정

#### Step 1: Helm install/upgrade 실행
```bash
helm upgrade multi-agent-system ./helm/multi-agent-system -n agent-system
```

#### Step 2: values.yaml 읽기
```yaml
# values.yaml
global:
  redis:
    host: "redis"
    port: 6379
    db: 0
```

#### Step 3: 템플릿 렌더링
```yaml
# 렌더링 전
- name: REDIS_HOST
  value: {{ .Values.global.redis.host | quote }}

# 렌더링 후
- name: REDIS_HOST
  value: "redis"
```

#### Step 4: Kubernetes에 적용
```bash
# Helm이 내부적으로 실행
kubectl apply -f <렌더링된 YAML>
```

### 폴더 구조의 의미

**중요:** 폴더 이름(redis, router-agent 등)은 **조직화를 위한 것일 뿐**입니다!

```
templates/
├── redis/              # 폴더 이름은 중요하지 않음
│   ├── deployment.yaml # ← 파일 내용의 "kind: Deployment"가 중요
│   └── service.yaml    # ← 파일 내용의 "kind: Service"가 중요
└── my-custom-name/     # 폴더 이름을 바꿔도 동작함
    └── deployment.yaml
```

**Helm이 보는 것:**
- ✅ 파일 내용 (kind, metadata, spec)
- ❌ 폴더 이름

---

## Kubernetes DNS 작동 원리

### CoreDNS 시스템

Kubernetes에는 **CoreDNS**라는 내장 DNS 서버가 있습니다.

```
┌─────────────────────────────────────────┐
│  Kubernetes Cluster                     │
│                                          │
│  ┌────────────────────────────────┐    │
│  │  CoreDNS (kube-system)         │    │
│  │  - DNS 서버 역할                │    │
│  │  - Service → IP 매핑 저장       │    │
│  └────────────────────────────────┘    │
│              ▲                           │
│              │ DNS 질의                 │
│  ┌───────────┴──────────────┐          │
│  │  Router Agent Pod         │          │
│  │  /etc/resolv.conf:        │          │
│  │    nameserver 10.96.0.10  │          │
│  └───────────────────────────┘          │
└─────────────────────────────────────────┘
```

### DNS 레코드 자동 생성

#### Step 1: Service 생성
```yaml
apiVersion: v1
kind: Service
metadata:
  name: redis                    # ← DNS 이름
  namespace: agent-system
spec:
  clusterIP: 10.106.234.149      # ← Kubernetes 자동 할당
```

#### Step 2: CoreDNS가 감지
```
CoreDNS: "새 Service 발견!"
       → 이름: redis
       → namespace: agent-system
       → ClusterIP: 10.106.234.149
```

#### Step 3: DNS 레코드 생성
```
DNS 레코드 추가:
redis.agent-system.svc.cluster.local → 10.106.234.149
```

### Pod의 DNS 설정

모든 Pod는 자동으로 다음 설정을 받습니다:

```bash
# Pod 내부의 /etc/resolv.conf
nameserver 10.96.0.10                           # CoreDNS IP
search agent-system.svc.cluster.local           # 검색 도메인
       svc.cluster.local
       cluster.local
options ndots:5
```

### DNS 질의 과정

```python
# Python 코드
redis_client = redis.Redis(host="redis", port=6379)
```

**내부 동작:**

1. **"redis" 이름 해석 시도**
   ```
   DNS 질의: redis
   → 실패 (FQDN 아님)
   ```

2. **search 도메인 추가하여 재시도**
   ```
   DNS 질의: redis.agent-system.svc.cluster.local
   → 성공! IP: 10.106.234.149
   ```

3. **TCP 연결**
   ```
   Python → 10.106.234.149:6379
   ```

### DNS 이름 형식

Kubernetes에서 Service DNS 이름은:

```
<service-name>.<namespace>.svc.cluster.local
     ↓              ↓        ↓       ↓
   redis      agent-system  고정   고정
```

**접근 방법:**

| 위치 | 사용 가능한 이름 | 예시 |
|------|-----------------|------|
| **같은 namespace** | 짧은 이름 | `redis` |
| **다른 namespace** | namespace 포함 | `redis.agent-system` |
| **어디서나** | 완전한 FQDN | `redis.agent-system.svc.cluster.local` |

---

## 환경 변수 주입

### 설정 흐름

```
values.yaml
    ↓
Helm 템플릿 렌더링
    ↓
Deployment YAML
    ↓
Pod 환경 변수
    ↓
애플리케이션 코드
```

### 상세 과정

#### 1. values.yaml 정의
```yaml
# helm/multi-agent-system/values.yaml
global:
  redis:
    host: "redis"
    port: 6379
    db: 0
```

#### 2. Deployment 템플릿
```yaml
# templates/router-agent/deployment.yaml
env:
  - name: REDIS_HOST
    value: {{ .Values.global.redis.host | quote }}
  - name: REDIS_PORT
    value: {{ .Values.global.redis.port | quote }}
  - name: REDIS_DB
    value: {{ .Values.global.redis.db | quote }}
```

#### 3. Helm 렌더링 결과
```yaml
# 실제 Kubernetes에 전송되는 YAML
env:
  - name: REDIS_HOST
    value: "redis"
  - name: REDIS_PORT
    value: "6379"
  - name: REDIS_DB
    value: "0"
```

#### 4. Pod 시작 시 환경 변수 주입
```bash
# Pod 내부
$ echo $REDIS_HOST
redis

$ echo $REDIS_PORT
6379
```

#### 5. Python 코드에서 읽기
```python
# router-agent/app/config.py
class Settings(BaseSettings):
    redis_host: str = "localhost"  # 기본값
    redis_port: int = 6379

    class Config:
        env_file = ".env"

# 환경 변수 우선순위:
# 1. 환경 변수 REDIS_HOST (Kubernetes가 주입) → "redis" ✅
# 2. .env 파일
# 3. 코드 기본값 "localhost"
```

### 환경 변수 우선순위

```
1순위: Kubernetes 환경 변수 (Deployment에서 주입)
         ↓ (없으면)
2순위: .env 파일 (로컬 개발용)
         ↓ (없으면)
3순위: 코드 기본값
```

**Kubernetes 배포 시:**
```python
settings.redis_host
# → "redis" (환경 변수)
# → "localhost" 무시됨
```

**로컬 개발 시:**
```python
settings.redis_host
# → "localhost" (.env 또는 기본값)
```

---

## 전체 연결 흐름

### 1. 배포 단계

```
┌─────────────────────────────────────────┐
│ helm upgrade multi-agent-system         │
└───────────────┬─────────────────────────┘
                ↓
┌─────────────────────────────────────────┐
│ values.yaml 읽기                        │
│   global.redis.host: "redis"            │
└───────────────┬─────────────────────────┘
                ↓
┌─────────────────────────────────────────┐
│ Helm 템플릿 렌더링                      │
│   env.REDIS_HOST = "redis"              │
└───────────────┬─────────────────────────┘
                ↓
┌─────────────────────────────────────────┐
│ Kubernetes 리소스 생성                  │
│   - Redis Deployment                    │
│   - Redis Service (이름: redis)         │
│   - Router Agent Deployment             │
└───────────────┬─────────────────────────┘
                ↓
┌─────────────────────────────────────────┐
│ CoreDNS에 DNS 레코드 자동 등록          │
│   redis.agent-system.svc → 10.106.x.x   │
└─────────────────────────────────────────┘
```

### 2. 런타임 단계

```
┌─────────────────────────────────────────┐
│ Router Agent Pod 시작                   │
│   환경 변수: REDIS_HOST="redis"         │
└───────────────┬─────────────────────────┘
                ↓
┌─────────────────────────────────────────┐
│ Python 코드 실행                        │
│   redis.Redis(host="redis", port=6379)  │
└───────────────┬─────────────────────────┘
                ↓
┌─────────────────────────────────────────┐
│ DNS 질의                                │
│   "redis" → CoreDNS                     │
└───────────────┬─────────────────────────┘
                ↓
┌─────────────────────────────────────────┐
│ CoreDNS 응답                            │
│   redis → 10.106.234.149                │
└───────────────┬─────────────────────────┘
                ↓
┌─────────────────────────────────────────┐
│ TCP 연결                                │
│   Router Agent → 10.106.234.149:6379    │
└───────────────┬─────────────────────────┘
                ↓
┌─────────────────────────────────────────┐
│ kube-proxy 포워딩                       │
│   Service IP → Redis Pod IP             │
└───────────────┬─────────────────────────┘
                ↓
┌─────────────────────────────────────────┐
│ Redis Pod 요청 처리                     │
│   SET/GET 명령 실행                     │
└─────────────────────────────────────────┘
```

### 3. 네트워크 패킷 흐름

```
[Router Agent Pod]
  IP: 10.244.0.20
       ↓ DNS 질의
[CoreDNS]
  IP: 10.96.0.10
       ↓ 응답: 10.106.234.149
[Router Agent Pod]
       ↓ TCP SYN → 10.106.234.149:6379
[kube-proxy]
  (iptables/IPVS 규칙)
       ↓ 포워딩 → 10.244.0.15:6379
[Redis Pod]
  IP: 10.244.0.15
       ↓ 요청 처리
[Router Agent Pod]
       ↓ 응답 수신
```

---

## 핵심 요약

### Redis가 배포되는 방법
1. ✅ Helm Chart의 `templates/redis/*.yaml` 파일로 배포
2. ✅ `values.yaml`에서 설정 값 관리
3. ✅ Deployment, Service, ConfigMap, PVC 자동 생성
4. ✅ 폴더 이름은 중요하지 않음 (조직화용)

### 연결되는 방법
1. ✅ Kubernetes DNS(CoreDNS)를 통한 서비스 디스커버리
2. ✅ Service 이름 "redis"가 DNS 이름이 됨
3. ✅ 환경 변수로 호스트 정보 주입 (values.yaml → Deployment)
4. ✅ Python redis 라이브러리로 연결

### 핵심 장점
1. ✅ Pod IP 변경되어도 Service 이름은 그대로
2. ✅ 별도의 서비스 메시 없이 자동 로드밸런싱
3. ✅ 환경별로 values.yaml만 변경하면 됨
4. ✅ 설정 중복 없이 Single Source of Truth

---

## 참고 자료

- [트러블슈팅 가이드](./REDIS_TROUBLESHOOTING.md)
- [설정 관리](./CONFIGURATION_MANAGEMENT.md)
- [배포 워크플로우](./DEPLOYMENT_WORKFLOW.md)
