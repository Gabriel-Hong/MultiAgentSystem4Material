# Prometheus + Grafana 모니터링 구현 완료

## 📋 구현 내용

### 1. Prometheus Helm 차트 ✅
- **위치**: `helm/multi-agent-system/templates/monitoring/prometheus/`
- **구성 파일**:
  - `configmap.yaml`: Prometheus 설정 및 알림 규칙
  - `deployment.yaml`: Prometheus 서버 배포
  - `service.yaml`: Prometheus 서비스
  - `pvc.yaml`: 영구 스토리지 (20Gi)
  - `rbac.yaml`: ServiceAccount 및 권한 설정

### 2. Grafana Helm 차트 ✅
- **위치**: `helm/multi-agent-system/templates/monitoring/grafana/`
- **구성 파일**:
  - `deployment.yaml`: Grafana 서버 배포
  - `service.yaml`: Grafana 서비스
  - `pvc.yaml`: 영구 스토리지 (5Gi)
  - `datasource-configmap.yaml`: Prometheus 데이터 소스 설정
  - `dashboards-config.yaml`: 대시보드 프로비저닝 설정
  - `dashboards.yaml`: 4개의 사전 구성된 대시보드
    - 시스템 리소스 모니터링
    - API 성능 모니터링
    - 비즈니스 메트릭
    - 에러 추적
  - `secret.yaml`: Grafana 관리자 비밀번호

### 3. Router Agent 메트릭 구현 ✅
- **새 파일**: `router-agent/app/metrics.py`
  - Prometheus 메트릭 정의
  - 요청 추적 데코레이터
  - 분류 메트릭 추적
  - Agent 호출 메트릭 추적
  
- **수정 파일**:
  - `router-agent/app/main.py`: `/metrics` 엔드포인트 추가, 데코레이터 적용
  - `router-agent/app/intent_classifier.py`: 분류 시간 및 신뢰도 메트릭 추가
  - `router-agent/requirements.txt`: `prometheus-client==0.18.0` 추가

### 4. SDB Agent 메트릭 구현 ✅
- **새 파일**: `sdb-agent/app/metrics.py`
  - Flask용 Prometheus 메트릭 정의
  - 처리 시간 추적
  - Bitbucket API 호출 추적
  - LLM 호출 및 토큰 사용량 추적
  - PR 생성 성공/실패 추적
  
- **수정 파일**:
  - `sdb-agent/app/main.py`: `/metrics` 엔드포인트 추가, 데코레이터 적용
  - `sdb-agent/requirements.txt`: `prometheus-client==0.18.0` 추가

### 5. Agent Deployment Annotations ✅
- **수정 파일**:
  - `helm/multi-agent-system/templates/router-agent/deployment.yaml`
  - `helm/multi-agent-system/templates/sdb-agent/deployment.yaml`
  - Prometheus 스크래핑을 위한 annotations 추가:
    ```yaml
    prometheus.io/scrape: "true"
    prometheus.io/port: "5000"
    prometheus.io/path: "/metrics"
    ```

### 6. values.yaml 설정 ✅
- **수정 파일**: `helm/multi-agent-system/values.yaml`
- **추가된 설정**:
  ```yaml
  monitoring:
    enabled: true
    prometheus:
      enabled: true
      resources: {...}
      storage: 20Gi
      retention: 30d
    grafana:
      enabled: true
      adminUser: admin
      adminPassword: "admin123"
      resources: {...}
      storage: 5Gi
  ```

---

## 🚀 배포 방법

### 1. Docker 이미지 빌드 (Agent 코드 변경 반영)

```bash
# Router Agent 이미지 빌드
cd router-agent
docker build -t router-agent:1.0.0 .

# SDB Agent 이미지 빌드
cd ../sdb-agent
docker build -t sdb-agent:1.0.0 .

# Minikube에 이미지 로드 (Minikube 사용시)
minikube image load router-agent:1.0.0
minikube image load sdb-agent:1.0.0
```

### 2. Namespace 및 Secret 생성

```bash
# Namespace 생성
kubectl create namespace agent-system

# Secret 생성 (아직 없는 경우)
kubectl create secret generic agent-secrets \
  --from-literal=openai-api-key='YOUR_OPENAI_API_KEY' \
  --from-literal=bitbucket-access-token='YOUR_BITBUCKET_TOKEN' \
  --from-literal=bitbucket-username='YOUR_BITBUCKET_USERNAME' \
  -n agent-system
```

### 3. Helm Chart 배포

```bash
# 저장소 루트 디렉토리로 이동
cd c:\MIDAS\10_Source\GenerateSDBAgent_Applying_k8s

# Helm Chart 배포 (모니터링 포함)
helm install multi-agent-system ./helm/multi-agent-system \
  -n agent-system \
  --create-namespace
```

### 4. 배포 확인

```bash
# 모든 Pod 상태 확인
kubectl get pods -n agent-system

# 예상 출력:
# NAME                           READY   STATUS    RESTARTS   AGE
# router-agent-xxx-xxx           1/1     Running   0          1m
# sdb-agent-xxx-xxx              1/1     Running   0          1m
# prometheus-xxx-xxx             1/1     Running   0          1m
# grafana-xxx-xxx                1/1     Running   0          1m

# 서비스 확인
kubectl get svc -n agent-system

# PVC 확인
kubectl get pvc -n agent-system
```

---

## 📊 모니터링 접근

### Prometheus 접근

```bash
# Port Forward
kubectl port-forward svc/prometheus 9090:9090 -n agent-system

# 브라우저에서 접속
# http://localhost:9090

# Targets 페이지에서 메트릭 수집 확인
# http://localhost:9090/targets
```

### Grafana 접근

```bash
# Port Forward
kubectl port-forward svc/grafana 3000:3000 -n agent-system

# 브라우저에서 접속
# http://localhost:3000

# 로그인 정보:
# Username: admin
# Password: admin123 (values.yaml에서 변경 가능)
```

### 메트릭 직접 확인

```bash
# Router Agent 메트릭
kubectl port-forward svc/router-agent-svc 5000:5000 -n agent-system
curl http://localhost:5000/metrics

# SDB Agent 메트릭
kubectl port-forward svc/sdb-agent-svc 5001:5000 -n agent-system
curl http://localhost:5001/metrics
```

---

## 📈 주요 메트릭

### Router Agent 메트릭

| 메트릭 이름 | 타입 | 설명 |
|-----------|------|------|
| `router_requests_total` | Counter | 총 요청 수 (endpoint, status별) |
| `router_classification_duration_seconds` | Histogram | Intent 분류 소요 시간 |
| `router_agent_calls_total` | Counter | Agent 호출 횟수 (agent, status별) |
| `router_agent_call_duration_seconds` | Histogram | Agent 호출 소요 시간 |
| `router_errors_total` | Counter | 에러 발생 횟수 (error_type, agent별) |
| `router_active_requests` | Gauge | 현재 처리 중인 요청 수 |
| `router_classification_confidence` | Histogram | 분류 신뢰도 분포 |

### SDB Agent 메트릭

| 메트릭 이름 | 타입 | 설명 |
|-----------|------|------|
| `sdb_processing_duration_seconds` | Histogram | 총 처리 소요 시간 |
| `sdb_bitbucket_api_calls_total` | Counter | Bitbucket API 호출 횟수 |
| `sdb_llm_requests_total` | Counter | LLM 요청 횟수 |
| `sdb_llm_tokens_used_total` | Counter | LLM 토큰 사용량 |
| `sdb_pr_created_total` | Counter | PR 생성 횟수 (success/failed) |
| `sdb_files_modified_total` | Counter | 수정된 파일 수 |
| `sdb_errors_total` | Counter | 에러 발생 횟수 |
| `sdb_active_tasks` | Gauge | 현재 처리 중인 작업 수 |

---

## 🎯 Grafana 대시보드

### 1. 시스템 리소스 모니터링
- CPU 사용률
- 메모리 사용량
- 네트워크 I/O
- Pod 재시작 횟수

### 2. API 성능 모니터링
- 요청 처리량 (RPS)
- 응답 시간 (P50, P95, P99)
- 에러율
- 활성 요청 수

### 3. 비즈니스 메트릭
- 시간당 처리 건수
- Agent별 호출 비율
- LLM 토큰 사용량
- PR 생성 성공률

### 4. 에러 추적
- 에러 발생 추이
- 에러 유형별 분포
- Agent별 에러율

---

## ⚠️ 알림 규칙

다음 조건에서 알림이 트리거됩니다:

1. **RouterHighErrorRate**: Router Agent 에러율이 10% 초과 (2분간)
2. **SDBHighLatency**: SDB Agent P95 처리 시간이 10초 초과 (3분간)
3. **PodRestarting**: Pod가 15분간 재시작 발생
4. **HighCPUUsage**: CPU 사용률이 80% 초과 (5분간)
5. **HighMemoryUsage**: 메모리 사용률이 90% 초과 (5분간)

---

## 🔧 트러블슈팅

### Prometheus가 메트릭을 수집하지 못함

```bash
# Pod annotations 확인
kubectl get pod -n agent-system -l app=router-agent -o yaml | grep annotations -A 5

# 메트릭 엔드포인트 직접 테스트
kubectl exec -it <router-pod> -n agent-system -- curl localhost:5000/metrics

# Prometheus 로그 확인
kubectl logs -n agent-system -l app=prometheus
```

### Grafana에 데이터가 표시되지 않음

```bash
# Prometheus 데이터 소스 연결 확인
# Grafana UI > Configuration > Data Sources

# Prometheus 쿼리 직접 테스트
# Prometheus UI (http://localhost:9090)에서 쿼리 실행

# Grafana 로그 확인
kubectl logs -n agent-system -l app=grafana
```

### PVC가 Pending 상태

```bash
# StorageClass 확인
kubectl get storageclass

# Minikube의 경우 기본 storageClass가 자동 생성됨
# 없으면 다음 명령으로 활성화:
minikube addons enable storage-provisioner

# PVC 상태 확인
kubectl describe pvc prometheus-pvc -n agent-system
kubectl describe pvc grafana-pvc -n agent-system
```

---

## 📚 참고 문서

- [PHASE1_MONITORING.md](./docs/enhancement/PHASE1_MONITORING.md) - 상세 구현 가이드
- [OVERVIEW.md](./docs/enhancement/OVERVIEW.md) - 전체 고도화 계획
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)

---

## ✅ 다음 단계

Phase 1 (모니터링) 완료 후:

1. **1주일 운영**: 메트릭 데이터 수집 및 안정성 확인
2. **Phase 2**: Redis 캐싱 적용 (API 호출 70% 감소 목표)
3. **Phase 3**: PostgreSQL 이력 관리 (요청/응답 저장)
4. **Phase 4**: 통합 및 최적화

---

**구현 완료일**: 2025-10-26  
**다음 Phase**: [PHASE2_REDIS.md](./docs/enhancement/PHASE2_REDIS.md)

