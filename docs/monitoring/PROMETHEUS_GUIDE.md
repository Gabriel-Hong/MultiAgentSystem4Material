# Prometheus 완전 가이드

Prometheus를 사용하여 Multi-Agent 시스템을 효과적으로 모니터링하는 방법을 배워봅시다.

## 📋 목차

1. [Prometheus 기본 개념](#prometheus-기본-개념)
2. [UI 사용법](#ui-사용법)
3. [PromQL 쿼리 언어](#promql-쿼리-언어)
4. [메트릭 타입 이해](#메트릭-타입-이해)
5. [Histogram과 백분위수](#histogram과-백분위수)
6. [Alert 규칙](#alert-규칙)
7. [문제 해결](#문제-해결)

---

## Prometheus 기본 개념

### Prometheus란?

**Prometheus**는 오픈소스 시스템 모니터링 및 알림 도구입니다.

**주요 특징:**
- **시계열 데이터베이스**: 메트릭을 시간순으로 저장
- **Pull 방식**: 주기적으로 타겟에서 메트릭 수집 (15초마다)
- **PromQL**: 강력한 쿼리 언어
- **알림 기능**: 임계값 초과 시 알림

### 시스템 아키텍처

```
┌─────────────────┐
│  Router Agent   │ :5000/metrics
└────────┬────────┘
         │
         │ (15초마다 Pull)
         ▼
    ┌─────────────┐
    │ Prometheus  │ :9090
    └─────┬───────┘
          │
          │ (Query)
          ▼
      ┌─────────┐
      │ Grafana │ :3000
      └─────────┘
```

### 메트릭 수집 흐름

1. **Agent가 메트릭 노출**
   - Router Agent: `http://localhost:5000/metrics`
   - SDB Agent: `http://localhost:8000/metrics`

2. **Prometheus가 수집 (Scrape)**
   - 15초마다 `/metrics` 엔드포인트 호출
   - 텍스트 형식 메트릭 파싱
   - 시계열 DB에 저장

3. **사용자가 조회**
   - Prometheus UI에서 PromQL 쿼리
   - Grafana 대시보드로 시각화

---

## UI 사용법

### 접속

```bash
kubectl port-forward svc/prometheus 9090:9090 -n agent-system
```

**브라우저**: http://localhost:9090

### 주요 메뉴

#### 1. Graph (메인 페이지)

**Expression 입력창**
- PromQL 쿼리 입력
- Tab 키로 자동완성
- Ctrl/Cmd + Enter로 실행

**Table / Graph 탭**
- **Table**: 현재 값 표시
- **Graph**: 시계열 그래프

**시간 범위 선택**
- 우측 상단: 1h, 3h, 6h, 12h, 1d
- Custom: 직접 시간 설정

**예시:**
```promql
router_requests_total
```

#### 2. Status → Targets

**모니터링 대상 확인**

```
Endpoint                           State    Labels
http://router-agent:5000/metrics   UP       app=router-agent
http://sdb-agent:8000/metrics      UP       app=sdb-agent
```

**UP**: 정상 수집 중
**DOWN**: 연결 실패

**DOWN 상태 원인 파악:**
- Endpoint가 응답하지 않음
- 네트워크 문제
- Pod가 종료됨

**확인 방법:**
```bash
# Pod 상태 확인
kubectl get pods -n agent-system -l app=router-agent

# 직접 /metrics 호출 테스트
kubectl exec -n agent-system deployment/router-agent -- curl localhost:5000/metrics
```

#### 3. Status → Configuration

**prometheus.yml 설정 확인**

```yaml
scrape_configs:
  - job_name: 'router-agent'
    scrape_interval: 15s
    static_configs:
      - targets: ['router-agent:5000']
```

**주요 설정:**
- `scrape_interval`: 수집 주기 (기본 15초)
- `scrape_timeout`: 타임아웃 (기본 10초)
- `job_name`: 메트릭에 자동으로 `job` 레이블 추가

#### 4. Alerts

**발동된 알림 확인**

**예시:**
```
HighErrorRate (FIRING)
  최근 5분간 에러율이 10%를 초과했습니다.
  Current value: 15%
```

**상태:**
- **Inactive**: 정상
- **Pending**: 조건 만족 (아직 for 시간 미달)
- **Firing**: 알림 발동

---

## PromQL 쿼리 언어

### 기본 문법

#### 1. Instant Vector Selector (즉시 벡터)

**특정 메트릭의 현재 값**

```promql
router_requests_total
```

**결과:**
```
router_requests_total{endpoint="webhook", method="POST", status="success"} 150
router_requests_total{endpoint="health", method="GET", status="success"} 300
```

#### 2. Label Matcher (레이블 필터)

**특정 레이블만 선택**

```promql
# 정확히 일치 (=)
router_requests_total{status="success"}

# 정확히 불일치 (!=)
router_requests_total{status!="success"}

# 정규식 일치 (=~)
router_requests_total{endpoint=~"webhook|health"}

# 정규식 불일치 (!~)
router_requests_total{endpoint!~"metrics|favicon"}
```

#### 3. Range Vector Selector (범위 벡터)

**지난 N 시간의 데이터**

```promql
# 지난 5분
router_requests_total[5m]

# 지난 1시간
router_requests_total[1h]

# 지난 1일
router_requests_total[1d]
```

**결과 형식:**
```
router_requests_total{endpoint="webhook"} @1697000000 = 100
                                           @1697000015 = 102
                                           @1697000030 = 105
                                           ...
```

### 연산자

#### 산술 연산자

```promql
# 덧셈
router_requests_total + sdb_requests_total

# 나눗셈 (비율 계산)
sum(router_requests_total{status="success"}) /
sum(router_requests_total) * 100

# 곱셈
process_resident_memory_bytes / 1024 / 1024  # MB로 변환
```

#### 비교 연산자

```promql
# 100 초과
router_active_requests > 100

# 이하
process_resident_memory_bytes <= 1073741824  # 1GB
```

#### 논리 연산자

```promql
# AND
(router_active_requests > 10) and (router_errors_total > 5)

# OR
(router_errors_total > 100) or (sdb_errors_total > 50)
```

### 집계 함수

#### sum (합계)

```promql
# 전체 합
sum(router_requests_total)

# 레이블별 합
sum by (status) (router_requests_total)
```

**결과:**
```
{status="success"} 450
{status="error"} 50
```

#### avg (평균)

```promql
avg(process_resident_memory_bytes)
```

#### max / min (최대/최소)

```promql
max(router_active_requests)
min(router_active_requests)
```

#### count (개수)

```promql
# endpoint 종류 개수
count(count by (endpoint) (router_requests_total))
```

#### topk / bottomk (상위/하위 K개)

```promql
# 에러가 많은 상위 3개
topk(3, sum by (error_type) (router_errors_total))

# 가장 적게 호출된 하위 2개 endpoint
bottomk(2, sum by (endpoint) (router_requests_total))
```

### 시간 함수

#### rate (초당 증가율)

**Counter 메트릭에 사용**

```promql
rate(router_requests_total[1m])
```

**의미**: 지난 1분간 초당 평균 증가량

**결과:**
```
{endpoint="webhook"} 2.5  # 초당 2.5개 요청
```

**중요:**
- Counter는 계속 증가하므로 `rate()` 없이는 의미 없음
- 항상 Range Vector `[시간]`와 함께 사용

#### irate (순간 증가율)

**마지막 2개 데이터 포인트만 사용**

```promql
irate(router_requests_total[1m])
```

**rate vs irate:**
- **rate**: 평균 (부드러운 그래프, 추세 파악)
- **irate**: 순간 (급격한 변화 감지)

#### increase (증가량)

**지정 기간 동안의 총 증가량**

```promql
increase(router_requests_total[1h])
```

**의미**: 지난 1시간 동안 몇 개 증가했는지

**결과:**
```
{endpoint="webhook"} 9000  # 1시간에 9000개 요청
```

#### delta / deriv

**Gauge 메트릭의 변화량**

```promql
# 변화량
delta(router_active_requests[5m])

# 변화율 (미분)
deriv(router_active_requests[5m])
```

### 시간 이동 (Offset)

```promql
# 1시간 전 값
router_requests_total offset 1h

# 지난주 같은 시간과 비교
router_requests_total /
router_requests_total offset 1w
```

**결과:**
```
1.2  # 지난주보다 20% 증가
```

### 수학 함수

```promql
# 반올림
round(avg(router_classification_duration_seconds))

# 올림
ceil(avg(router_classification_duration_seconds))

# 내림
floor(avg(router_classification_duration_seconds))

# 절댓값
abs(delta(router_active_requests[5m]))

# 제곱근
sqrt(sum(router_requests_total))

# 로그
ln(sum(router_requests_total))
log2(sum(router_requests_total))
log10(sum(router_requests_total))
```

### 시간 범위 함수

```promql
# 지난 5분 중 최댓값
max_over_time(router_active_requests[5m])

# 지난 1시간 중 최솟값
min_over_time(router_active_requests[1h])

# 지난 10분 평균
avg_over_time(router_active_requests[10m])
```

---

## 메트릭 타입 이해

### 1. Counter (카운터)

**누적 합계** - 계속 증가만 함

**예시:**
- `router_requests_total`: 시작 후 총 요청 수
- `router_errors_total`: 시작 후 총 에러 수
- `sdb_pr_created_total`: 총 PR 생성 수

**특징:**
- 값이 계속 증가 (재시작 시 0으로 리셋)
- 절댓값은 의미 없음
- **반드시 `rate()` 또는 `increase()` 사용**

**올바른 사용:**
```promql
# ✅ 초당 요청 수
rate(router_requests_total[1m])

# ✅ 1시간 동안 발생한 에러
increase(router_errors_total[1h])
```

**잘못된 사용:**
```promql
# ❌ 의미 없음 (누적값)
router_requests_total
```

### 2. Gauge (게이지)

**현재 값** - 증가/감소 자유

**예시:**
- `router_active_requests`: 현재 처리 중인 요청
- `sdb_active_tasks`: 현재 작업 중인 태스크
- `process_resident_memory_bytes`: 현재 메모리 사용량

**특징:**
- 현재 상태를 나타냄
- 올라갔다 내려갔다 가능
- 그대로 사용해도 의미 있음

**사용 예:**
```promql
# ✅ 현재 활성 요청
router_active_requests

# ✅ 평균 활성 요청 (지난 5분)
avg_over_time(router_active_requests[5m])

# ✅ 최대 활성 요청 (지난 1시간)
max_over_time(router_active_requests[1h])
```

### 3. Histogram (히스토그램)

**분포를 추적** - 값들이 어느 범위에 분포하는지

**예시:**
- `router_classification_duration_seconds`: 분류 시간 분포
- `sdb_processing_duration_seconds`: 처리 시간 분포

**구성 요소:**
1. **Buckets** (`_bucket`): 각 범위에 몇 개
2. **Sum** (`_sum`): 총 합
3. **Count** (`_count`): 총 개수

**실제 메트릭:**
```
# Buckets
router_classification_duration_seconds_bucket{le="0.1"} 5
router_classification_duration_seconds_bucket{le="0.5"} 12
router_classification_duration_seconds_bucket{le="1.0"} 25
router_classification_duration_seconds_bucket{le="2.0"} 40
router_classification_duration_seconds_bucket{le="+Inf"} 50

# Sum
router_classification_duration_seconds_sum 75.3

# Count
router_classification_duration_seconds_count 50
```

**해석:**
- 0.1초 이하: 5개
- 0.5초 이하: 12개 (0.1~0.5 사이는 7개)
- 평균: 75.3 / 50 = 1.5초

**사용 예:**
```promql
# 평균 시간
rate(router_classification_duration_seconds_sum[5m]) /
rate(router_classification_duration_seconds_count[5m])

# P95 (백분위수)
histogram_quantile(0.95,
  rate(router_classification_duration_seconds_bucket[5m])
)
```

### 4. Summary (요약)

**사전 계산된 백분위수** (이 프로젝트에서는 미사용)

**Histogram vs Summary:**
- **Histogram**: 서버에서 계산 (유연함, 집계 가능)
- **Summary**: 클라이언트에서 계산 (정확하지만 집계 불가)

---

## Histogram과 백분위수

### 백분위수란?

**PXX (Percentile)**: 전체의 XX%가 이 값 이하

**예시:**
- **P50 (중앙값)**: 50%의 요청이 이 시간 이하
- **P95**: 95%의 요청이 이 시간 이하
- **P99**: 99%의 요청이 이 시간 이하

**왜 중요한가?**

평균만으로는 부족합니다!

**예시:**
```
요청 100개
- 90개: 1초
- 9개: 2초
- 1개: 100초

평균: 2.89초 (괜찮아 보임)
P99: 100초 (1%는 100초 걸림!)
```

→ **P99를 보면 최악의 경우를 파악 가능**

### histogram_quantile 함수

**문법:**
```promql
histogram_quantile(백분위수, rate(메트릭_bucket[시간]))
```

**예시:**

**P50 (중앙값):**
```promql
histogram_quantile(0.50,
  rate(router_classification_duration_seconds_bucket[5m])
)
```

**P95:**
```promql
histogram_quantile(0.95,
  rate(router_classification_duration_seconds_bucket[5m])
)
```

**P99:**
```promql
histogram_quantile(0.99,
  rate(router_classification_duration_seconds_bucket[5m])
)
```

### Buckets 설정

**router_classification_duration_seconds 설정:**
```python
buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
```

**의미:**
- 0.1초 이하
- 0.1~0.5초
- 0.5~1.0초
- 1.0~2.0초
- 2.0~5.0초
- 5.0~10.0초
- 10.0초 초과

**좋은 Buckets 설정:**
- 예상 범위를 잘 커버
- 너무 많지 않게 (10개 내외)
- 로그 스케일 (0.1, 0.5, 1, 2, 5, 10, ...)

### 다중 레이블 Histogram

**agent별로 분리:**
```promql
histogram_quantile(0.95,
  sum by (le, agent) (
    rate(router_agent_call_duration_seconds_bucket[5m])
  )
)
```

**주의사항:**
- `le` 레이블 반드시 포함 (`le` = less than or equal)
- `sum by` 사용 시 `le` 포함 필수

---

## Alert 규칙

### Alert 규칙 구조

**예시:**
```yaml
groups:
  - name: multi_agent_alerts
    interval: 15s
    rules:
      - alert: HighErrorRate
        expr: |
          sum(rate(router_errors_total[5m])) /
          sum(rate(router_requests_total[5m])) * 100 > 10
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "에러율이 10% 초과"
          description: "현재 에러율: {{ $value }}%"
```

**구성 요소:**

1. **alert**: 알림 이름
2. **expr**: PromQL 조건식
3. **for**: 이 시간 동안 지속되면 발동
4. **labels**: 알림 메타데이터
5. **annotations**: 알림 메시지

### Alert 상태

**3가지 상태:**

1. **Inactive (비활성)**
   - 조건 미충족
   - 정상 상태

2. **Pending (대기)**
   - 조건 충족 중
   - `for` 시간 경과 전
   - 예: `for: 2m`이면 2분 대기

3. **Firing (발동)**
   - 조건 충족
   - `for` 시간 경과
   - 알림 전송

### 실전 Alert 규칙

#### 1. 높은 에러율

```yaml
- alert: HighErrorRate
  expr: |
    sum(rate(router_errors_total[5m])) /
    sum(rate(router_requests_total[5m])) * 100 > 10
  for: 2m
  labels:
    severity: warning
  annotations:
    summary: "에러율이 10% 초과"
    description: "현재 에러율: {{ $value }}%"
```

#### 2. 응답 시간 느림

```yaml
- alert: SlowResponseTime
  expr: |
    histogram_quantile(0.95,
      rate(router_classification_duration_seconds_bucket[5m])
    ) > 10
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "P95 응답 시간이 10초 초과"
    description: "현재 P95: {{ $value }}초"
```

#### 3. 서비스 다운

```yaml
- alert: ServiceDown
  expr: up{job="router-agent"} == 0
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "Router Agent가 응답하지 않음"
    description: "{{ $labels.instance }} 다운"
```

#### 4. 높은 메모리 사용

```yaml
- alert: HighMemoryUsage
  expr: |
    process_resident_memory_bytes / 1024 / 1024 > 1024
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "메모리 사용량이 1GB 초과"
    description: "현재: {{ $value }}MB"
```

### Alert 템플릿 변수

**사용 가능한 변수:**

- `{{ $value }}`: 현재 값
- `{{ $labels.label_name }}`: 레이블 값
- `{{ $externalLabels }}`: 외부 레이블

**예시:**
```yaml
annotations:
  summary: "{{ $labels.job }}에서 에러 발생"
  description: "에러 타입: {{ $labels.error_type }}, 현재 값: {{ $value }}"
```

---

## 문제 해결

### Targets가 DOWN 상태

**증상:**
```
Status → Targets에서 DOWN 표시
```

**원인 1: Pod가 종료됨**
```bash
kubectl get pods -n agent-system -l app=router-agent

# 재시작
kubectl rollout restart deployment/router-agent -n agent-system
```

**원인 2: /metrics 엔드포인트 문제**
```bash
# Pod 내부에서 직접 호출
kubectl exec -n agent-system deployment/router-agent -- curl localhost:5000/metrics

# 응답 없으면 코드 확인 필요
```

**원인 3: 네트워크 설정**
```bash
# Service 확인
kubectl get svc -n agent-system router-agent-svc

# Endpoint 확인
kubectl get endpoints -n agent-system router-agent-svc
```

### 메트릭이 안 보임

**증상:**
```
쿼리 결과: No data
```

**확인 1: Targets 상태**
```
Status → Targets → UP인지 확인
```

**확인 2: 메트릭 이름 오타**
```promql
# 존재하는 메트릭 목록 확인
{__name__=~"router.*"}
```

**확인 3: 시간 범위**
```
우측 상단 시간 범위를 넓게 (1d, 1w 등)
```

**확인 4: 레이블 필터**
```promql
# 레이블 없이 시도
router_requests_total

# 특정 레이블만
router_requests_total{status="success"}
```

### 그래프가 이상함

**증상:**
```
Counter 메트릭이 계속 증가만 함
```

**원인:**
```
Counter는 누적값이므로 rate() 없이는 증가만 함
```

**해결:**
```promql
# ❌
router_requests_total

# ✅
rate(router_requests_total[1m])
```

### 쿼리가 너무 느림

**증상:**
```
쿼리 실행에 10초 이상 소요
```

**원인:**
```
- 시간 범위가 너무 넓음 (1w, 1M)
- 너무 많은 시계열 (카디널리티 폭발)
```

**해결:**
```promql
# 시간 범위 줄이기
rate(router_requests_total[1d])  # [1w] → [1d]

# 레이블 집계
sum by (status) (router_requests_total)  # endpoint 제거
```

### Alert가 안 발동됨

**확인 1: expr 조건**
```
Prometheus Graph에서 직접 expr 실행
→ 값이 나와야 함
```

**확인 2: for 시간**
```yaml
for: 5m  # 5분 동안 지속되어야 발동
```

**확인 3: Alertmanager**
```bash
# Alertmanager가 실행 중인지
kubectl get pods -n agent-system -l app=alertmanager
```

---

## 모범 사례

### 1. 쿼리 최적화

**나쁜 예:**
```promql
sum(router_requests_total)
```

**좋은 예:**
```promql
sum(rate(router_requests_total[1m]))
```

### 2. 레이블 선택

**나쁜 예:**
```promql
# 모든 레이블 포함 (카디널리티 폭발)
router_requests_total{method="POST", endpoint="webhook", status="success", instance="...", pod="..."}
```

**좋은 예:**
```promql
# 필요한 레이블만
sum by (endpoint, status) (router_requests_total)
```

### 3. 시간 범위 설정

**권장:**
- 실시간 모니터링: `[1m]` ~ `[5m]`
- 트렌드 분석: `[1h]` ~ `[6h]`
- 장기 추세: `[1d]` ~ `[1w]`

### 4. Alert 임계값

**현실적인 값 설정:**
```yaml
# ❌ 너무 엄격
expr: error_rate > 0.1  # 0.1% 초과 시 알림

# ✅ 적절
expr: error_rate > 5  # 5% 초과 시 알림
```

---

## 다음 단계

- [Grafana 가이드](GRAFANA_GUIDE.md) - 시각화와 대시보드
- [PromQL 쿼리 모음](PROMQL_QUERIES.md) - 즉시 사용 가능한 쿼리
- [빠른 시작](MONITORING_QUICKSTART.md) - 5분 튜토리얼

---

**Prometheus 마스터하기 완료!** 🎉
