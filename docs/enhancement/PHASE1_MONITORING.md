# Phase 1: Prometheus + Grafana 모니터링 구축

## 문서 정보
- **Phase**: 1 / 4
- **예상 기간**: 2주 (Week 1-2)
- **난이도**: ⭐⭐⭐ (중)
- **선행 요구사항**: Kubernetes 클러스터 운영 중

---

## 목차
1. [개요](#개요)
2. [아키텍처](#아키텍처)
3. [구현 단계](#구현-단계)
4. [Prometheus 구축](#prometheus-구축)
5. [Grafana 구축](#grafana-구축)
6. [Agent 메트릭 통합](#agent-메트릭-통합)
7. [대시보드 구성](#대시보드-구성)
8. [알림 설정](#알림-설정)
9. [테스트 및 검증](#테스트-및-검증)
10. [트러블슈팅](#트러블슈팅)

---

## 개요

### 목표
- 시스템 전체의 메트릭을 실시간으로 수집하고 시각화
- 성능 병목 지점 파악 및 장애 조기 감지
- 비즈니스 메트릭 추적 (이슈 처리 건수, 성공률 등)

### 예상 효과
- ✅ **가시성**: 시스템 상태를 한눈에 파악
- ✅ **장애 감지**: 평균 30분 → 5분 이내
- ✅ **성능 최적화**: 병목 지점 식별 및 개선
- ✅ **용량 계획**: 리소스 사용 패턴 분석

### 수집할 메트릭 카테고리

| 카테고리 | 메트릭 예시 | 용도 |
|---------|------------|------|
| **시스템 리소스** | CPU, 메모리, 네트워크 I/O | 리소스 모니터링 |
| **API 성능** | 응답 시간, 처리량, 에러율 | 성능 모니터링 |
| **비즈니스** | 이슈 처리 건수, Agent별 호출 수 | 비즈니스 분석 |
| **비용** | LLM 토큰 사용량, API 호출 수 | 비용 추적 |

---

## 아키텍처

### 모니터링 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                        │
│                                                               │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Router Agent                                       │    │
│  │  GET /metrics → Prometheus 메트릭 노출             │    │
│  └───────────────────────┬────────────────────────────┘    │
│                          │                                   │
│  ┌────────────────────────────────────────────────────┐    │
│  │  SDB Agent                                          │    │
│  │  GET /metrics → Prometheus 메트릭 노출             │    │
│  └───────────────────────┬────────────────────────────┘    │
│                          │                                   │
│                          ↓                                   │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Prometheus                                         │    │
│  │  - ServiceMonitor로 자동 탐지                       │    │
│  │  - 15초 간격 메트릭 수집 (scrape_interval)         │    │
│  │  - 알림 규칙 평가                                   │    │
│  │  - 데이터 저장 (30일)                               │    │
│  └───────────────────────┬────────────────────────────┘    │
│                          │                                   │
│                          ↓                                   │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Grafana                                            │    │
│  │  - Prometheus를 데이터 소스로 사용                  │    │
│  │  - 4개 대시보드 제공                                │    │
│  │  - 알림 채널 설정 (Slack, Email)                   │    │
│  └────────────────────────────────────────────────────┘    │
└───────────────────────────────────────────────────────────┘
```

### 데이터 흐름

```
Agent (/metrics)
    ↓ [15초마다 scrape]
Prometheus
    ↓ [실시간 쿼리]
Grafana Dashboard
    ↓ [알림 조건 충족시]
Alertmanager → Slack/Email
```

---

## 구현 단계

### Week 1: Prometheus 구축
- [ ] Day 1-2: Prometheus Helm 차트 작성
- [ ] Day 3-4: Router Agent 메트릭 구현
- [ ] Day 5: SDB Agent 메트릭 구현

### Week 2: Grafana 및 대시보드
- [ ] Day 1-2: Grafana 배포 및 설정
- [ ] Day 3-4: 대시보드 구성 (4개)
- [ ] Day 5: 알림 규칙 설정 및 테스트

---

## Prometheus 구축

### 1. Prometheus ConfigMap

**파일**: `helm/multi-agent-system/templates/monitoring/prometheus/configmap.yaml`

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: {{ .Values.global.namespace }}
  labels:
    app: prometheus
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s  # 15초마다 메트릭 수집
      evaluation_interval: 15s  # 15초마다 알림 규칙 평가
      external_labels:
        cluster: {{ .Values.global.environment }}
        namespace: {{ .Values.global.namespace }}

    # 알림 규칙 파일
    rule_files:
      - /etc/prometheus/rules/*.yml

    # 메트릭 수집 대상
    scrape_configs:
      # Router Agent 메트릭 수집
      - job_name: 'router-agent'
        kubernetes_sd_configs:
          - role: pod
            namespaces:
              names:
                - {{ .Values.global.namespace }}
        relabel_configs:
          # app=router-agent 레이블을 가진 Pod만 수집
          - source_labels: [__meta_kubernetes_pod_label_app]
            action: keep
            regex: router-agent
          # Pod 이름을 instance 레이블로 설정
          - source_labels: [__meta_kubernetes_pod_name]
            target_label: instance
          # 메트릭 경로 설정
          - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
            action: replace
            target_label: __metrics_path__
            regex: (.+)
          # 포트 설정
          - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
            action: replace
            regex: ([^:]+)(?::\d+)?;(\d+)
            replacement: $1:$2
            target_label: __address__

      # SDB Agent 메트릭 수집
      - job_name: 'sdb-agent'
        kubernetes_sd_configs:
          - role: pod
            namespaces:
              names:
                - {{ .Values.global.namespace }}
        relabel_configs:
          - source_labels: [__meta_kubernetes_pod_label_app]
            action: keep
            regex: sdb-agent
          - source_labels: [__meta_kubernetes_pod_name]
            target_label: instance
          - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
            action: replace
            target_label: __metrics_path__
            regex: (.+)
          - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
            action: replace
            regex: ([^:]+)(?::\d+)?;(\d+)
            replacement: $1:$2
            target_label: __address__

      # Kubernetes Pod 메트릭 (cAdvisor)
      - job_name: 'kubernetes-pods'
        kubernetes_sd_configs:
          - role: pod
        relabel_configs:
          - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
            action: keep
            regex: true
          - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
            action: replace
            target_label: __metrics_path__
            regex: (.+)
          - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
            action: replace
            regex: ([^:]+)(?::\d+)?;(\d+)
            replacement: $1:$2
            target_label: __address__
          - action: labelmap
            regex: __meta_kubernetes_pod_label_(.+)
          - source_labels: [__meta_kubernetes_namespace]
            target_label: kubernetes_namespace
          - source_labels: [__meta_kubernetes_pod_name]
            target_label: kubernetes_pod_name

  # 알림 규칙
  alert-rules.yml: |
    groups:
      - name: agent_alerts
        interval: 30s
        rules:
          # Router Agent 에러율 급증
          - alert: RouterHighErrorRate
            expr: |
              rate(router_errors_total[5m]) > 0.1
            for: 2m
            labels:
              severity: warning
              component: router-agent
            annotations:
              summary: "Router Agent 에러율 급증"
              description: "최근 5분간 에러율이 10%를 초과했습니다. (현재: {{ $value | humanizePercentage }})"

          # SDB Agent 처리 시간 급증
          - alert: SDBHighLatency
            expr: |
              histogram_quantile(0.95, rate(sdb_processing_duration_seconds_bucket[5m])) > 10
            for: 3m
            labels:
              severity: warning
              component: sdb-agent
            annotations:
              summary: "SDB Agent 처리 시간 급증"
              description: "P95 처리 시간이 10초를 초과했습니다. (현재: {{ $value }}초)"

          # Pod 재시작 빈번
          - alert: PodRestarting
            expr: |
              rate(kube_pod_container_status_restarts_total{namespace="agent-system"}[15m]) > 0
            for: 5m
            labels:
              severity: critical
            annotations:
              summary: "Pod 재시작 발생"
              description: "{{ $labels.pod }}가 최근 15분간 재시작되었습니다."

          # CPU 사용률 높음
          - alert: HighCPUUsage
            expr: |
              rate(container_cpu_usage_seconds_total{namespace="agent-system"}[5m]) > 0.8
            for: 5m
            labels:
              severity: warning
            annotations:
              summary: "CPU 사용률 높음"
              description: "{{ $labels.pod }}의 CPU 사용률이 80%를 초과했습니다."

          # 메모리 사용률 높음
          - alert: HighMemoryUsage
            expr: |
              container_memory_usage_bytes{namespace="agent-system"} / container_spec_memory_limit_bytes{namespace="agent-system"} > 0.9
            for: 5m
            labels:
              severity: critical
            annotations:
              summary: "메모리 사용률 높음"
              description: "{{ $labels.pod }}의 메모리 사용률이 90%를 초과했습니다."
```

### 2. Prometheus Deployment

**파일**: `helm/multi-agent-system/templates/monitoring/prometheus/deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: prometheus
  namespace: {{ .Values.global.namespace }}
  labels:
    app: prometheus
spec:
  replicas: 1
  selector:
    matchLabels:
      app: prometheus
  template:
    metadata:
      labels:
        app: prometheus
    spec:
      serviceAccountName: prometheus
      containers:
        - name: prometheus
          image: prom/prometheus:v2.45.0
          args:
            - '--config.file=/etc/prometheus/prometheus.yml'
            - '--storage.tsdb.path=/prometheus'
            - '--storage.tsdb.retention.time=30d'
            - '--web.enable-lifecycle'
            - '--web.enable-admin-api'
          ports:
            - containerPort: 9090
              name: web
          volumeMounts:
            - name: config
              mountPath: /etc/prometheus
            - name: rules
              mountPath: /etc/prometheus/rules
            - name: storage
              mountPath: /prometheus
          resources:
            requests:
              cpu: 500m
              memory: 1Gi
            limits:
              cpu: 1000m
              memory: 2Gi
          livenessProbe:
            httpGet:
              path: /-/healthy
              port: 9090
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /-/ready
              port: 9090
            initialDelaySeconds: 10
            periodSeconds: 5
      volumes:
        - name: config
          configMap:
            name: prometheus-config
            items:
              - key: prometheus.yml
                path: prometheus.yml
        - name: rules
          configMap:
            name: prometheus-config
            items:
              - key: alert-rules.yml
                path: alert-rules.yml
        - name: storage
          persistentVolumeClaim:
            claimName: prometheus-pvc
```

### 3. Prometheus Service

**파일**: `helm/multi-agent-system/templates/monitoring/prometheus/service.yaml`

```yaml
apiVersion: v1
kind: Service
metadata:
  name: prometheus
  namespace: {{ .Values.global.namespace }}
  labels:
    app: prometheus
spec:
  type: ClusterIP
  ports:
    - port: 9090
      targetPort: 9090
      protocol: TCP
      name: web
  selector:
    app: prometheus
```

### 4. Prometheus PVC

**파일**: `helm/multi-agent-system/templates/monitoring/prometheus/pvc.yaml`

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: prometheus-pvc
  namespace: {{ .Values.global.namespace }}
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 20Gi
  {{- if .Values.monitoring.prometheus.storageClassName }}
  storageClassName: {{ .Values.monitoring.prometheus.storageClassName }}
  {{- end }}
```

### 5. Prometheus RBAC

**파일**: `helm/multi-agent-system/templates/monitoring/prometheus/rbac.yaml`

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: prometheus
  namespace: {{ .Values.global.namespace }}
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: prometheus
rules:
  - apiGroups: [""]
    resources:
      - nodes
      - nodes/proxy
      - services
      - endpoints
      - pods
    verbs: ["get", "list", "watch"]
  - apiGroups: ["extensions"]
    resources:
      - ingresses
    verbs: ["get", "list", "watch"]
  - nonResourceURLs: ["/metrics"]
    verbs: ["get"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: prometheus
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: prometheus
subjects:
  - kind: ServiceAccount
    name: prometheus
    namespace: {{ .Values.global.namespace }}
```

---

## Grafana 구축

### 1. Grafana Deployment

**파일**: `helm/multi-agent-system/templates/monitoring/grafana/deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: grafana
  namespace: {{ .Values.global.namespace }}
  labels:
    app: grafana
spec:
  replicas: 1
  selector:
    matchLabels:
      app: grafana
  template:
    metadata:
      labels:
        app: grafana
    spec:
      containers:
        - name: grafana
          image: grafana/grafana:10.0.3
          ports:
            - containerPort: 3000
              name: web
          env:
            - name: GF_SECURITY_ADMIN_USER
              value: admin
            - name: GF_SECURITY_ADMIN_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: grafana-admin
                  key: password
            - name: GF_SERVER_ROOT_URL
              value: "http://localhost:3000"
            - name: GF_INSTALL_PLUGINS
              value: ""
          volumeMounts:
            - name: storage
              mountPath: /var/lib/grafana
            - name: datasources
              mountPath: /etc/grafana/provisioning/datasources
            - name: dashboards-config
              mountPath: /etc/grafana/provisioning/dashboards
            - name: dashboards
              mountPath: /var/lib/grafana/dashboards
          resources:
            requests:
              cpu: 250m
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 512Mi
          livenessProbe:
            httpGet:
              path: /api/health
              port: 3000
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /api/health
              port: 3000
            initialDelaySeconds: 10
            periodSeconds: 5
      volumes:
        - name: storage
          persistentVolumeClaim:
            claimName: grafana-pvc
        - name: datasources
          configMap:
            name: grafana-datasources
        - name: dashboards-config
          configMap:
            name: grafana-dashboards-config
        - name: dashboards
          configMap:
            name: grafana-dashboards
```

### 2. Grafana DataSource ConfigMap

**파일**: `helm/multi-agent-system/templates/monitoring/grafana/datasource-configmap.yaml`

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-datasources
  namespace: {{ .Values.global.namespace }}
data:
  datasources.yaml: |
    apiVersion: 1
    datasources:
      - name: Prometheus
        type: prometheus
        access: proxy
        url: http://prometheus:9090
        isDefault: true
        editable: true
        jsonData:
          timeInterval: 15s
```

### 3. Grafana Service

**파일**: `helm/multi-agent-system/templates/monitoring/grafana/service.yaml`

```yaml
apiVersion: v1
kind: Service
metadata:
  name: grafana
  namespace: {{ .Values.global.namespace }}
  labels:
    app: grafana
spec:
  type: ClusterIP
  ports:
    - port: 3000
      targetPort: 3000
      protocol: TCP
      name: web
  selector:
    app: grafana
```

---

## Agent 메트릭 통합

### Router Agent 메트릭 구현

**파일**: `router-agent/app/metrics.py` (신규 생성)

```python
"""
Prometheus 메트릭 정의 및 수집
"""
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from prometheus_client import CONTENT_TYPE_LATEST
from fastapi.responses import Response
import time
from functools import wraps


# 메트릭 정의
router_requests_total = Counter(
    'router_requests_total',
    'Total number of requests received by router',
    ['method', 'endpoint', 'status']
)

router_classification_duration_seconds = Histogram(
    'router_classification_duration_seconds',
    'Time spent on intent classification',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

router_agent_calls_total = Counter(
    'router_agent_calls_total',
    'Total number of agent calls',
    ['agent', 'status']
)

router_agent_call_duration_seconds = Histogram(
    'router_agent_call_duration_seconds',
    'Time spent calling agents',
    ['agent'],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

router_errors_total = Counter(
    'router_errors_total',
    'Total number of errors',
    ['error_type', 'agent']
)

router_active_requests = Gauge(
    'router_active_requests',
    'Number of requests currently being processed'
)

router_classification_confidence = Histogram(
    'router_classification_confidence',
    'Confidence score of intent classification',
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)


def track_request_metrics(endpoint: str):
    """요청 메트릭 추적 데코레이터"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            router_active_requests.inc()
            start_time = time.time()
            status = 'success'

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = 'error'
                router_errors_total.labels(
                    error_type=type(e).__name__,
                    agent='router'
                ).inc()
                raise
            finally:
                duration = time.time() - start_time
                router_active_requests.dec()
                router_requests_total.labels(
                    method='POST',
                    endpoint=endpoint,
                    status=status
                ).inc()

        return wrapper
    return decorator


def track_classification(func):
    """분류 메트릭 추적 데코레이터"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()

        try:
            result = func(*args, **kwargs)

            # 분류 소요 시간 기록
            duration = time.time() - start_time
            router_classification_duration_seconds.observe(duration)

            # 신뢰도 기록
            if isinstance(result, dict) and 'confidence' in result:
                router_classification_confidence.observe(result['confidence'])

            return result
        except Exception as e:
            router_errors_total.labels(
                error_type=type(e).__name__,
                agent='classification'
            ).inc()
            raise

    return wrapper


def track_agent_call(agent_name: str):
    """Agent 호출 메트릭 추적 데코레이터"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = 'success'

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = 'error'
                router_errors_total.labels(
                    error_type=type(e).__name__,
                    agent=agent_name
                ).inc()
                raise
            finally:
                duration = time.time() - start_time
                router_agent_call_duration_seconds.labels(
                    agent=agent_name
                ).observe(duration)
                router_agent_calls_total.labels(
                    agent=agent_name,
                    status=status
                ).inc()

        return wrapper
    return decorator


def get_metrics_response():
    """메트릭 엔드포인트 응답 생성"""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
```

**파일**: `router-agent/app/main.py` (수정)

```python
# 기존 import에 추가
from .metrics import (
    track_request_metrics,
    track_classification,
    track_agent_call,
    get_metrics_response
)

# 메트릭 엔드포인트 추가
@app.get("/metrics")
async def metrics():
    """Prometheus 메트릭 엔드포인트"""
    return get_metrics_response()


# 기존 webhook 엔드포인트 수정
@app.post("/webhook")
@track_request_metrics("webhook")
async def route_webhook(request: Request):
    # 기존 코드...

    # Classification에 메트릭 추가
    from .metrics import router_classification_duration_seconds

    # Agent 호출에 메트릭 추가
    @track_agent_call(agent_name)
    async def call_agent():
        async with httpx.AsyncClient(timeout=agent.timeout) as client:
            # 기존 agent 호출 코드
            pass

    result = await call_agent()
    # 나머지 코드...
```

**파일**: `router-agent/requirements.txt` (추가)

```txt
prometheus-client==0.18.0
```

### SDB Agent 메트릭 구현

**파일**: `sdb-agent/app/metrics.py` (신규 생성)

```python
"""
Prometheus 메트릭 정의 및 수집 (Flask용)
"""
from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import Counter, Histogram, Gauge
import time
from functools import wraps


# Flask app에서 초기화 필요
metrics = None  # app.py에서 설정


# 커스텀 메트릭 정의
sdb_processing_duration_seconds = Histogram(
    'sdb_processing_duration_seconds',
    'Time spent processing SDB requests',
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0]
)

sdb_bitbucket_api_calls_total = Counter(
    'sdb_bitbucket_api_calls_total',
    'Total Bitbucket API calls',
    ['api_type', 'status']  # api_type: get_file, create_branch, create_pr 등
)

sdb_llm_requests_total = Counter(
    'sdb_llm_requests_total',
    'Total LLM requests',
    ['model', 'status']
)

sdb_llm_tokens_used_total = Counter(
    'sdb_llm_tokens_used_total',
    'Total LLM tokens used',
    ['model', 'token_type']  # token_type: prompt, completion
)

sdb_pr_created_total = Counter(
    'sdb_pr_created_total',
    'Total PRs created',
    ['status']  # success, failed
)

sdb_files_modified_total = Counter(
    'sdb_files_modified_total',
    'Total files modified'
)

sdb_errors_total = Counter(
    'sdb_errors_total',
    'Total errors',
    ['error_type', 'component']
)

sdb_active_tasks = Gauge(
    'sdb_active_tasks',
    'Number of tasks currently being processed'
)


def track_processing_time(func):
    """처리 시간 추적 데코레이터"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        sdb_active_tasks.inc()
        start_time = time.time()

        try:
            result = func(*args, **kwargs)
            return result
        finally:
            duration = time.time() - start_time
            sdb_processing_duration_seconds.observe(duration)
            sdb_active_tasks.dec()

    return wrapper


def track_bitbucket_call(api_type: str):
    """Bitbucket API 호출 추적 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            status = 'success'

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                status = 'error'
                sdb_errors_total.labels(
                    error_type=type(e).__name__,
                    component='bitbucket_api'
                ).inc()
                raise
            finally:
                sdb_bitbucket_api_calls_total.labels(
                    api_type=api_type,
                    status=status
                ).inc()

        return wrapper
    return decorator


def track_llm_call(model: str):
    """LLM 호출 추적 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            status = 'success'

            try:
                result = func(*args, **kwargs)

                # 토큰 사용량 기록
                if isinstance(result, dict) and 'usage' in result:
                    usage = result['usage']
                    sdb_llm_tokens_used_total.labels(
                        model=model,
                        token_type='prompt'
                    ).inc(usage.get('prompt_tokens', 0))

                    sdb_llm_tokens_used_total.labels(
                        model=model,
                        token_type='completion'
                    ).inc(usage.get('completion_tokens', 0))

                return result
            except Exception as e:
                status = 'error'
                sdb_errors_total.labels(
                    error_type=type(e).__name__,
                    component='llm'
                ).inc()
                raise
            finally:
                sdb_llm_requests_total.labels(
                    model=model,
                    status=status
                ).inc()

        return wrapper
    return decorator
```

**파일**: `sdb-agent/app/main.py` (수정)

```python
from prometheus_flask_exporter import PrometheusMetrics
from app import metrics as custom_metrics

# Flask app 초기화 후
metrics = PrometheusMetrics(app)

# 기본 메트릭 제외 (커스텀 메트릭만 사용)
metrics.info('sdb_agent_info', 'SDB Agent Information', version='1.0.0')


# process 엔드포인트에 메트릭 추가
@app.route('/process', methods=['POST'])
@custom_metrics.track_processing_time
def process_handler():
    # 기존 코드...
    pass
```

**파일**: `sdb-agent/requirements.txt` (추가)

```txt
prometheus-flask-exporter==0.22.4
prometheus-client==0.18.0
```

### Agent Deployment Annotations 추가

**파일**: `helm/multi-agent-system/templates/router-agent/deployment.yaml` (수정)

```yaml
spec:
  template:
    metadata:
      labels:
        app: router-agent
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "5000"
        prometheus.io/path: "/metrics"
```

**파일**: `helm/multi-agent-system/templates/sdb-agent/deployment.yaml` (수정)

```yaml
spec:
  template:
    metadata:
      labels:
        app: sdb-agent
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "5000"
        prometheus.io/path: "/metrics"
```

---

## 대시보드 구성

### 대시보드 1: 시스템 리소스

**목적**: Pod별 CPU, 메모리, 네트워크 사용량 모니터링

**주요 패널**:
1. CPU 사용률 (%)
2. 메모리 사용량 (MB)
3. 네트워크 I/O (bytes/sec)
4. Pod 재시작 횟수
5. HPA 상태 (현재/최소/최대 Replica 수)

**PromQL 쿼리 예시**:
```promql
# CPU 사용률
rate(container_cpu_usage_seconds_total{namespace="agent-system"}[5m]) * 100

# 메모리 사용량
container_memory_usage_bytes{namespace="agent-system"} / 1024 / 1024

# 네트워크 수신
rate(container_network_receive_bytes_total{namespace="agent-system"}[5m])
```

### 대시보드 2: API 성능

**목적**: 응답 시간, 처리량, 에러율 모니터링

**주요 패널**:
1. 요청 처리량 (RPS)
2. 응답 시간 (P50, P95, P99)
3. 에러율 (%)
4. 활성 요청 수
5. Agent별 호출 분포

**PromQL 쿼리 예시**:
```promql
# 요청 처리량 (RPS)
rate(router_requests_total[5m])

# P95 응답 시간
histogram_quantile(0.95, rate(router_agent_call_duration_seconds_bucket[5m]))

# 에러율
rate(router_errors_total[5m]) / rate(router_requests_total[5m]) * 100
```

### 대시보드 3: 비즈니스 메트릭

**목적**: 이슈 처리 건수, Agent별 성능, 비용 추적

**주요 패널**:
1. 시간당 처리 건수
2. Agent별 호출 비율
3. 평균 처리 시간
4. LLM 토큰 사용량 (시간별, Agent별)
5. PR 생성 성공률

**PromQL 쿼리 예시**:
```promql
# 시간당 처리 건수
increase(router_requests_total{status="success"}[1h])

# Agent별 호출 비율
sum by(agent) (rate(router_agent_calls_total[5m]))

# LLM 토큰 사용량
sum(rate(sdb_llm_tokens_used_total[1h]))
```

### 대시보드 4: 에러 추적

**목적**: 에러 유형별 분석 및 트렌드 파악

**주요 패널**:
1. 에러 발생 추이
2. 에러 유형별 분포
3. Agent별 에러율
4. 최근 에러 로그 (Loki 연동시)

**PromQL 쿼리 예시**:
```promql
# 에러 발생 추이
rate(router_errors_total[5m])

# 에러 유형별 분포
sum by(error_type) (increase(router_errors_total[1h]))
```

---

## 알림 설정

### Alertmanager 설정 (옵션)

알림을 Slack이나 Email로 전송하려면 Alertmanager를 추가로 배포합니다.

**파일**: `helm/multi-agent-system/templates/monitoring/alertmanager/config.yaml`

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: alertmanager-config
  namespace: {{ .Values.global.namespace }}
data:
  alertmanager.yml: |
    global:
      slack_api_url: {{ .Values.monitoring.alertmanager.slackWebhookUrl }}

    route:
      receiver: 'slack-notifications'
      group_by: ['alertname', 'severity']
      group_wait: 10s
      group_interval: 10s
      repeat_interval: 12h

    receivers:
      - name: 'slack-notifications'
        slack_configs:
          - channel: '#agent-alerts'
            title: 'Agent System Alert'
            text: '{{ range .Alerts }}{{ .Annotations.summary }}\n{{ .Annotations.description }}\n{{ end }}'
            send_resolved: true
```

---

## 테스트 및 검증

### 1. Prometheus 접근 테스트

```bash
# Port forward
kubectl port-forward svc/prometheus 9090:9090 -n agent-system

# 브라우저에서 접속
http://localhost:9090

# 메트릭 확인
# Targets 메뉴에서 router-agent, sdb-agent가 UP 상태인지 확인
```

### 2. Grafana 접근 테스트

```bash
# Port forward
kubectl port-forward svc/grafana 3000:3000 -n agent-system

# 브라우저에서 접속
http://localhost:3000

# 로그인 (admin / 설정한 비밀번호)
# Data Sources에서 Prometheus 연결 확인
```

### 3. 메트릭 수집 확인

```bash
# Router Agent 메트릭 직접 확인
kubectl port-forward svc/router-agent-svc 5000:5000 -n agent-system
curl http://localhost:5000/metrics

# 예상 출력:
# router_requests_total{endpoint="/webhook",method="POST",status="success"} 10
# router_classification_duration_seconds_bucket{le="1.0"} 8
```

### 4. 알림 테스트

의도적으로 에러를 발생시켜 알림이 트리거되는지 확인:

```bash
# 잘못된 요청 전송하여 에러 발생
for i in {1..20}; do
  curl -X POST http://router-agent/webhook \
    -H "Content-Type: application/json" \
    -d '{"invalid": "payload"}'
done

# Prometheus에서 알림 규칙 확인
# Alerts 메뉴에서 RouterHighErrorRate가 Firing 상태인지 확인
```

---

## 검증 체크리스트

- [ ] Prometheus가 배포되고 정상 동작함
- [ ] Grafana가 배포되고 Prometheus와 연결됨
- [ ] Router Agent `/metrics` 엔드포인트가 메트릭을 반환함
- [ ] SDB Agent `/metrics` 엔드포인트가 메트릭을 반환함
- [ ] Prometheus가 두 Agent에서 메트릭을 수집함 (Targets UP)
- [ ] 4개 대시보드가 모두 데이터를 표시함
- [ ] 알림 규칙이 설정되고 테스트 통과
- [ ] 실제 Webhook 요청 시 메트릭이 증가함
- [ ] Pod 재시작 시 데이터가 유지됨 (PVC 확인)

---

## 트러블슈팅

### 문제 1: Prometheus가 Agent 메트릭을 수집하지 못함

**증상**: Targets 페이지에서 Agent가 DOWN 상태

**원인**:
- Pod annotations 누락
- 네트워크 정책으로 인한 차단
- `/metrics` 엔드포인트 오류

**해결**:
```bash
# Annotations 확인
kubectl get pod -n agent-system -l app=router-agent -o yaml | grep annotations -A 5

# 메트릭 엔드포인트 직접 테스트
kubectl exec -it <router-pod> -n agent-system -- curl localhost:5000/metrics

# Prometheus 로그 확인
kubectl logs -n agent-system -l app=prometheus
```

### 문제 2: Grafana 대시보드에 데이터가 표시되지 않음

**원인**:
- Prometheus 데이터 소스 미설정
- 쿼리 오류
- 시간 범위 설정 오류

**해결**:
```bash
# Prometheus 쿼리 직접 테스트
# Prometheus UI에서 쿼리 실행하여 데이터 확인

# Grafana 로그 확인
kubectl logs -n agent-system -l app=grafana
```

### 문제 3: 메트릭 수집 지연

**원인**:
- scrape_interval이 너무 김
- 대량의 메트릭으로 인한 부하

**해결**:
```yaml
# Prometheus ConfigMap 수정
global:
  scrape_interval: 10s  # 15s → 10s로 변경
```

---

## 다음 단계

Phase 1 완료 후:
1. ✅ 모니터링 시스템 안정화 확인 (1주일 운영)
2. ✅ 메트릭 데이터 분석하여 최적화 포인트 파악
3. → [PHASE2_REDIS.md](./PHASE2_REDIS.md) 진행

---

**문서 버전**: 1.0.0
**최종 업데이트**: 2025-10-22
