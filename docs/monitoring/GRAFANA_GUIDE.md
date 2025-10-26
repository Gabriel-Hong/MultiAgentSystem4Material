# Grafana 완전 가이드

Grafana를 사용하여 Multi-Agent 시스템의 메트릭을 효과적으로 시각화하는 방법을 배워봅시다.

## 📋 목차

1. [Grafana 기본 개념](#grafana-기본-개념)
2. [대시보드 사용법](#대시보드-사용법)
3. [패널 생성과 편집](#패널-생성과-편집)
4. [변수 (Variables) 사용](#변수-variables-사용)
5. [알림 설정](#알림-설정)
6. [고급 기능](#고급-기능)
7. [문제 해결](#문제-해결)

---

## Grafana 기본 개념

### Grafana란?

**Grafana**는 메트릭 데이터를 시각화하는 오픈소스 대시보드 플랫폼입니다.

**주요 특징:**
- **다양한 데이터 소스**: Prometheus, InfluxDB, MySQL 등
- **실시간 대시보드**: 자동 새로고침
- **알림 기능**: 임계값 초과 시 Slack, Email 등으로 알림
- **공유 가능**: 대시보드 JSON 내보내기/가져오기

### 시스템 아키텍처

```
┌─────────────┐
│ Prometheus  │ :9090
└──────┬──────┘
       │
       │ (PromQL 쿼리)
       ▼
   ┌─────────┐
   │ Grafana │ :3000
   └────┬────┘
        │
        │ (대시보드 표시)
        ▼
    ┌───────┐
    │ 사용자 │
    └───────┘
```

### 접속

```bash
kubectl port-forward svc/grafana 3000:3000 -n agent-system
```

**브라우저**: http://localhost:3000

**기본 로그인:**
- Username: `admin`
- Password: `admin123`

---

## 대시보드 사용법

### 대시보드 열기

**좌측 메뉴:**
```
📊 Dashboards → Browse
```

**사전 구성된 대시보드:**
1. **API Performance Monitoring** - 요청 처리 성능
2. **Business Metrics** - 비즈니스 지표
3. **Error Tracking** - 에러 모니터링
4. **System Resources Monitoring** - 시스템 리소스

### 시간 범위 조정

**우측 상단:**
```
[Last 6 hours ▼]
```

**옵션:**
- Last 5 minutes
- Last 15 minutes
- Last 30 minutes
- Last 1 hour
- Last 3 hours
- Last 6 hours
- Last 12 hours
- Last 24 hours
- Last 2 days
- Last 7 days
- Last 30 days
- Custom range (직접 지정)

**Custom 예시:**
```
From: 2024-01-15 09:00:00
To: 2024-01-15 18:00:00
```

### 자동 새로고침

**우측 상단:**
```
[⏱️ Off ▼]
```

**옵션:**
- 5s (5초마다)
- 10s
- 30s
- 1m
- 5m
- 15m
- 30m
- 1h

**실시간 모니터링:**
```
5s ~ 30s 추천
```

### 패널 확대/축소

**패널 제목 클릭 → View**
- 전체 화면으로 패널 표시
- ESC로 나가기

**패널 제목 클릭 → Edit**
- 패널 편집 모드

### 대시보드 저장

**우측 상단:**
```
💾 Save dashboard
```

**옵션:**
- Save: 현재 대시보드 저장
- Save As: 다른 이름으로 저장
- Cancel changes: 변경사항 취소

---

## 패널 생성과 편집

### 새 패널 추가

**대시보드에서:**
```
우측 상단 → Add panel → Add a new panel
```

### 패널 편집 화면

#### 1. Query 섹션

**Data Source 선택:**
```
Prometheus (default)
```

**PromQL 쿼리 입력:**
```promql
rate(router_requests_total[1m])
```

**Legend 설정:**
```
{{endpoint}} - {{status}}
```

**결과:**
```
webhook - success
health - success
```

#### 2. Visualization 섹션

**패널 타입 선택**

##### Time series (시계열 그래프)

**용도**: 시간에 따른 변화

**설정:**
- **Line width**: 선 굵기 (1-10)
- **Fill opacity**: 채우기 투명도 (0-100)
- **Point size**: 점 크기 (0-40)
- **Show points**: auto / always / never

**예시 쿼리:**
```promql
rate(router_requests_total[1m])
```

##### Stat (숫자 표시)

**용도**: 현재 값을 크게 표시

**설정:**
- **Show**: Value / Name / Value and name
- **Value**: Last / First / Min / Max / Mean
- **Orientation**: Auto / Horizontal / Vertical

**예시 쿼리:**
```promql
router_active_requests
```

##### Gauge (게이지)

**용도**: 범위 내 현재 위치

**설정:**
- **Min**: 최솟값 (예: 0)
- **Max**: 최댓값 (예: 100)
- **Thresholds**: 임계값 (예: 80=yellow, 90=red)

**예시 쿼리:**
```promql
sum(rate(router_errors_total[5m])) /
sum(rate(router_requests_total[5m])) * 100
```

##### Bar gauge (막대 게이지)

**용도**: 여러 항목 비교

**설정:**
- **Orientation**: Horizontal / Vertical
- **Display mode**: Basic / LCD / Gradient

**예시 쿼리:**
```promql
sum by (agent) (router_agent_calls_total)
```

##### Pie chart (파이 차트)

**용도**: 비율 시각화

**설정:**
- **Pie type**: Pie / Donut
- **Legend**: Show / Hide
- **Labels**: Name / Percent / Value

**예시 쿼리:**
```promql
sum by (status) (router_requests_total)
```

##### Table (테이블)

**용도**: 상세 데이터 표시

**설정:**
- **Columns**: 표시할 컬럼 선택
- **Sort**: 정렬 기준

**예시 쿼리:**
```promql
sum by (error_type) (router_errors_total)
```

#### 3. Panel options 섹션

**Title**: 패널 제목
```
Request Rate (RPS)
```

**Description**: 설명
```
초당 요청 수 (Requests Per Second)
```

**Transparent background**: 투명 배경
```
☑️ 체크 시 배경 투명
```

#### 4. Standard options 섹션

**Unit**: 단위 설정

- **Short**: 1000 → 1K
- **Percent (0-100)**: 0.95 → 95%
- **Bytes (IEC)**: 1073741824 → 1.0 GiB
- **Seconds (s)**: 3.5 → 3.50s
- **Requests/sec (rps)**: 요청/초

**Decimals**: 소수점 자리
```
2 → 12.34
0 → 12
```

**Min / Max**: 축 범위
```
Min: 0
Max: 100 (또는 auto)
```

**Thresholds**: 임계값 색상
```
Base: green
80: yellow
90: red
```

#### 5. Value mappings

**값을 텍스트로 변환**

**예시:**
```
Value: 0 → Text: "Inactive"
Value: 1 → Text: "Active"
```

#### 6. Overrides

**특정 시리즈만 스타일 변경**

**예시:**
```
Fields with name matching: error
→ Color: red
→ Fill opacity: 50
```

### 패널 예시

#### 예시 1: 초당 요청 수 (RPS)

**Query:**
```promql
sum(rate(router_requests_total[1m]))
```

**Settings:**
- Visualization: Time series
- Unit: Requests/sec (rps)
- Title: "Request Rate (RPS)"
- Legend: hidden

#### 예시 2: 응답 시간 백분위수

**Query A (P50):**
```promql
histogram_quantile(0.50,
  rate(router_classification_duration_seconds_bucket[5m])
)
```

**Query B (P95):**
```promql
histogram_quantile(0.95,
  rate(router_classification_duration_seconds_bucket[5m])
)
```

**Query C (P99):**
```promql
histogram_quantile(0.99,
  rate(router_classification_duration_seconds_bucket[5m])
)
```

**Settings:**
- Visualization: Time series
- Unit: Seconds (s)
- Title: "Response Time Percentiles"
- Legend: `P{{quantile}}`

#### 예시 3: 에러율 게이지

**Query:**
```promql
sum(rate(router_errors_total[5m])) /
sum(rate(router_requests_total[5m])) * 100
```

**Settings:**
- Visualization: Gauge
- Unit: Percent (0-100)
- Min: 0
- Max: 100
- Thresholds:
  - 0: green
  - 5: yellow
  - 10: red
- Title: "Error Rate (%)"

#### 예시 4: Agent 호출 분포

**Query:**
```promql
sum by (agent) (router_agent_calls_total)
```

**Settings:**
- Visualization: Pie chart
- Pie type: Donut
- Legend: Show
- Labels: Percent
- Title: "Agent Call Distribution"

---

## 변수 (Variables) 사용

### 변수란?

**대시보드를 동적으로 만드는 기능**

**예시:**
```
원래: router_requests_total{endpoint="webhook"}
변수 사용: router_requests_total{endpoint="$endpoint"}
```

**장점:**
- 하나의 패널로 여러 케이스 표시
- 드롭다운으로 선택
- 대시보드 재사용성 향상

### 변수 생성

**Settings ⚙️ → Variables → Add variable**

#### 변수 타입

##### 1. Query (쿼리 기반)

**예시: Endpoint 선택**

**Name:**
```
endpoint
```

**Label:**
```
Endpoint
```

**Data source:**
```
Prometheus
```

**Query:**
```promql
label_values(router_requests_total, endpoint)
```

**결과:**
```
webhook
health
metrics
```

**Refresh:**
```
On dashboard load
```

**Multi-value:**
```
☑️ 체크 시 여러 개 선택 가능
```

**Include All option:**
```
☑️ 체크 시 "All" 옵션 추가
```

##### 2. Custom (수동 입력)

**예시: 시간 범위**

**Name:**
```
time_range
```

**Label:**
```
Time Range
```

**Type:**
```
Custom
```

**Custom options:**
```
1m : 1 minute
5m : 5 minutes
1h : 1 hour
1d : 1 day
```

##### 3. Constant (상수)

**예시: 임계값**

**Name:**
```
error_threshold
```

**Value:**
```
10
```

### 변수 사용

**쿼리에서:**
```promql
router_requests_total{endpoint="$endpoint"}
```

**패널 제목에서:**
```
Requests - $endpoint
```

**All 선택 시:**
```promql
router_requests_total{endpoint=~"$endpoint"}
```

**정규식 매칭 필요** (`=` → `=~`)

### 변수 예시

#### 예시 1: Endpoint 필터

**변수 생성:**
```
Name: endpoint
Query: label_values(router_requests_total, endpoint)
Multi-value: ✅
Include All: ✅
```

**쿼리에서 사용:**
```promql
sum by (endpoint) (
  rate(router_requests_total{endpoint=~"$endpoint"}[1m])
)
```

**결과:**
- Dropdown에서 선택: webhook, health, 또는 All
- 선택에 따라 그래프 필터링

#### 예시 2: Agent 선택

**변수 생성:**
```
Name: agent
Query: label_values(router_agent_calls_total, agent)
```

**쿼리에서 사용:**
```promql
sum(router_agent_calls_total{agent="$agent"})
```

#### 예시 3: 시간 범위 (템플릿)

**변수 생성:**
```
Name: interval
Type: Custom
Options:
  1m : 1분
  5m : 5분
  1h : 1시간
```

**쿼리에서 사용:**
```promql
rate(router_requests_total[$interval])
```

---

## 알림 설정

### Grafana Alerting

**Grafana 8.0+부터 새로운 알림 시스템**

### Alert Rule 생성

**좌측 메뉴:**
```
🔔 Alerting → Alert rules → New alert rule
```

#### 1. Define query and alert condition

**Rule name:**
```
High Error Rate Alert
```

**Query A:**
```promql
sum(rate(router_errors_total[5m])) /
sum(rate(router_requests_total[5m])) * 100
```

**Condition:**
```
WHEN last() OF query(A) IS ABOVE 10
```

**의미**: 쿼리 A의 마지막 값이 10 초과 시

#### 2. Define alert details

**Folder:**
```
Multi-Agent System
```

**Evaluation group:**
```
system-health (새로 만들기)
```

**Evaluation interval:**
```
1m (1분마다 평가)
```

**For:**
```
2m (2분 동안 지속 시 알림)
```

#### 3. Add annotations

**Summary:**
```
에러율이 10%를 초과했습니다
```

**Description:**
```
현재 에러율: {{ $values.A.Value }}%
지난 5분간 평균값입니다.
```

**Runbook URL:**
```
https://wiki.example.com/troubleshooting/high-error-rate
```

#### 4. Configure labels

**Labels:**
```
severity: warning
team: backend
service: router-agent
```

**용도**: 알림 라우팅 및 필터링

### Contact Points (알림 채널)

**Alerting → Contact points → Add contact point**

#### Slack 연동

**Name:**
```
Slack - Alerts
```

**Integration:**
```
Slack
```

**Webhook URL:**
```
https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

**Username:**
```
Grafana Alert
```

**Optional Slack Settings:**
- Recipient: `#alerts` (채널명)
- Title: `{{ .GroupLabels.alertname }}`
- Text: `{{ .Annotations.summary }}`

#### Email 연동

**Name:**
```
Email - Team
```

**Integration:**
```
Email
```

**Addresses:**
```
devops@example.com
backend-team@example.com
```

**Message:**
```
{{ .Annotations.description }}
```

#### Webhook 연동

**Name:**
```
Custom Webhook
```

**Integration:**
```
Webhook
```

**URL:**
```
https://your-service.com/webhook
```

**HTTP Method:**
```
POST
```

### Notification Policies (라우팅)

**Alerting → Notification policies**

**정책 트리 구조:**

```
Default policy (Slack - Alerts)
├─ severity=critical → Email + Slack
├─ severity=warning → Slack only
└─ team=backend → Slack - Backend
```

**매칭 레이블:**
```
severity = critical
```

**Contact point:**
```
Email - Team
```

**Continue matching:**
```
☑️ 체크 시 다음 정책도 확인
```

### Silence (알림 일시 중지)

**Alerting → Silences → Add silence**

**Duration:**
```
1h (1시간 동안)
2024-01-15 14:00 ~ 2024-01-15 15:00
```

**Matchers:**
```
alertname = HighErrorRate
severity = warning
```

**Comment:**
```
점검 작업 중 (Maintenance)
```

---

## 고급 기능

### 대시보드 공유

#### 1. Snapshot

**Share → Snapshot**

- **Snapshot name**: Multi-Agent Dashboard
- **Expire**: 1 hour / 1 day / 1 week / Never
- **Publish to snapshot.raintank.io**: 공개 공유

**URL 생성:**
```
https://snapshots.raintank.io/dashboard/snapshot/abc123xyz
```

#### 2. Export JSON

**Share → Export → Save to file**

**다른 Grafana에 가져오기:**
```
➕ → Import → Upload JSON file
```

#### 3. Link

**Share → Link**

- **Short URL**: 짧은 URL 생성
- **Lock time range**: 현재 시간 범위 고정
- **Theme**: Current / Dark / Light

### Annotations (주석)

**대시보드에 이벤트 표시**

#### 수동 주석

**그래프에서 Ctrl + 클릭**

**Text:**
```
배포 완료 v1.2.3
```

**Tags:**
```
deployment, production
```

#### 쿼리 기반 주석

**Dashboard settings → Annotations → Add annotation query**

**Name:**
```
Deployments
```

**Data source:**
```
Prometheus
```

**Query:**
```promql
changes(process_start_time_seconds[1m]) > 0
```

**의미**: 프로세스 재시작 시점 표시

### Transformations (데이터 변환)

**패널 편집 → Transform**

#### 1. Filter by name

**필드 선택/제외**

**예시:**
```
Include: endpoint, value
Exclude: __name__, job
```

#### 2. Rename by regex

**정규식으로 이름 변경**

**Match:**
```
(.*)_total
```

**Replace:**
```
$1
```

**결과:**
```
router_requests_total → router_requests
```

#### 3. Organize fields

**컬럼 순서 변경 및 숨기기**

#### 4. Join by field

**여러 쿼리 결합**

**Field:**
```
Time
```

#### 5. Add field from calculation

**계산 필드 추가**

**Mode:**
```
Binary operation
```

**Operation:**
```
A / B * 100
```

**Alias:**
```
success_rate
```

### Playlist (자동 전환)

**Dashboards → Playlists → New playlist**

**Name:**
```
Monitoring Rotation
```

**Add dashboards:**
```
1. API Performance Monitoring
2. Business Metrics
3. Error Tracking
4. System Resources
```

**Interval:**
```
30s (30초마다 전환)
```

**Play:**
```
▶️ Start playlist
```

**용도**: 모니터링 화면에 상시 표시

---

## 문제 해결

### 데이터가 안 보임

**증상:**
```
Panel: "No data"
```

**확인 1: Data source 연결**
```
⚙️ Configuration → Data sources → Prometheus
→ Test 버튼 클릭
```

**확인 2: 쿼리 오류**
```
Query inspector (i 아이콘) → Stats → Errors 확인
```

**확인 3: 시간 범위**
```
우측 상단 시간 범위를 넓게 (Last 24 hours)
```

**확인 4: Prometheus 확인**
```
Prometheus UI에서 직접 쿼리 테스트
```

### 그래프가 너무 복잡함

**증상:**
```
너무 많은 시리즈 (100개 이상)
```

**해결 1: 집계**
```promql
# 전: endpoint별로 모두 표시
router_requests_total

# 후: status별로만 집계
sum by (status) (router_requests_total)
```

**해결 2: Limit series**
```
Query options → Limit → 10
```

**해결 3: Legend 숨기기**
```
Legend → Mode → Hidden
```

### 알림이 안 옴

**확인 1: Alert Rule 상태**
```
Alerting → Alert rules
→ State: Normal / Pending / Firing 확인
```

**확인 2: Contact Point 테스트**
```
Alerting → Contact points
→ 해당 contact point 선택 → Test
```

**확인 3: Notification Policy**
```
Alerting → Notification policies
→ 매칭 레이블 확인
```

**확인 4: Silence 확인**
```
Alerting → Silences
→ 활성화된 silence가 있는지 확인
```

### 성능 문제

**증상:**
```
대시보드 로딩이 느림 (10초 이상)
```

**해결 1: 쿼리 최적화**
```promql
# 전: 모든 레이블
router_requests_total

# 후: 필요한 레이블만
sum by (endpoint, status) (router_requests_total)
```

**해결 2: 시간 범위 줄이기**
```
Last 24 hours → Last 6 hours
```

**해결 3: Resolution 낮추기**
```
Query options → Min interval → 30s
```

**해결 4: 패널 수 줄이기**
```
너무 많은 패널 (20개 이상) → 10개 이하로
```

---

## 모범 사례

### 1. 대시보드 구성

**계층 구조:**
```
상단: 핵심 지표 (Stat, Gauge)
중단: 시계열 그래프 (Time series)
하단: 상세 테이블 (Table)
```

**예시:**
```
┌──────────────────────────────────┐
│  RPS: 150  │  P95: 3s  │  Errors │
├──────────────────────────────────┤
│  [Request Rate Graph]            │
│  [Response Time Graph]           │
├──────────────────────────────────┤
│  [Error Details Table]           │
└──────────────────────────────────┘
```

### 2. 색상 사용

**일관된 색상 스키마:**
- **녹색**: 정상, 성공
- **노란색**: 경고
- **빨간색**: 위험, 에러
- **파란색**: 정보

### 3. 단위 설정

**항상 적절한 단위 설정:**
- 시간: Seconds (s)
- 메모리: Bytes (IEC)
- 비율: Percent (0-100)
- 요청: Requests/sec (rps)

### 4. Legend 정리

**의미 있는 Legend:**
```promql
# 전
{{__name__}}

# 후
{{endpoint}} - {{status}}
```

### 5. 문서화

**패널 Description 작성:**
```
이 그래프는 초당 요청 수를 보여줍니다.
5% 이하: 트래픽 없음
10-100: 정상
100 초과: 높은 부하
```

---

## 유용한 단축키

| 단축키 | 기능 |
|--------|------|
| `d` + `k` | 대시보드 검색 |
| `d` + `h` | 홈으로 |
| `Ctrl/Cmd` + `S` | 대시보드 저장 |
| `e` | 패널 편집 모드 |
| `v` | 패널 보기 모드 |
| `ESC` | 전체화면 종료 |
| `Ctrl/Cmd` + `K` | Command palette |

---

## 다음 단계

- [Prometheus 가이드](PROMETHEUS_GUIDE.md) - PromQL 마스터하기
- [PromQL 쿼리 모음](PROMQL_QUERIES.md) - 즉시 사용 가능한 쿼리
- [빠른 시작](MONITORING_QUICKSTART.md) - 5분 튜토리얼

---

**Grafana 마스터하기 완료!** 🎉
