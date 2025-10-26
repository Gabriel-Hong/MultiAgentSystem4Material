# 모니터링 빠른 시작 가이드

5분 안에 Prometheus와 Grafana를 사용하여 Multi-Agent 시스템을 모니터링하는 방법을 배워봅시다!

## 📋 목차

1. [준비 사항](#준비-사항)
2. [Prometheus 시작하기](#prometheus-시작하기)
3. [Grafana 시작하기](#grafana-시작하기)
4. [첫 번째 모니터링](#첫-번째-모니터링)
5. [다음 단계](#다음-단계)

---

## 준비 사항

### 확인 사항

```bash
# 1. Agent들이 실행 중인지 확인
kubectl get pods -n agent-system

# 예상 출력:
# NAME                           READY   STATUS    RESTARTS   AGE
# router-agent-xxx               1/1     Running   0          10m
# sdb-agent-xxx                  1/1     Running   0          10m
# prometheus-xxx                 1/1     Running   0          10m
# grafana-xxx                    1/1     Running   0          10m
```

모든 Pod가 `Running` 상태여야 합니다.

---

## Prometheus 시작하기

### 1단계: Prometheus 접속

```bash
# 새 터미널 창 열기
kubectl port-forward svc/prometheus 9090:9090 -n agent-system
```

**브라우저에서 접속:**
```
http://localhost:9090
```

### 2단계: Targets 확인

**상단 메뉴: Status → Targets**

다음 항목들이 **UP** 상태인지 확인:
```
✅ router-agent (1/1 up)
✅ sdb-agent (1/1 up)
```

DOWN 상태라면:
```bash
# Pod 상태 확인
kubectl get pods -n agent-system

# Pod 로그 확인
kubectl logs -n agent-system -l app=router-agent
```

### 3단계: 첫 번째 쿼리 실행

**상단 메뉴: Graph**

**Expression 입력창에 입력:**
```promql
router_requests_total
```

**Execute 버튼 클릭**

**Table 탭에서 결과 확인:**
```
router_requests_total{endpoint="webhook", method="POST", status="success"} = 3
```

**Graph 탭으로 전환:**
- 시계열 그래프로 확인
- 시간 범위 선택: 1h, 3h, 6h 등

### 4단계: 더 유용한 쿼리

**초당 요청 수 (RPS):**
```promql
rate(router_requests_total[1m])
```

**평균 응답 시간:**
```promql
rate(router_classification_duration_seconds_sum[5m]) /
rate(router_classification_duration_seconds_count[5m])
```

**에러 발생 확인:**
```promql
router_errors_total
```

---

## Grafana 시작하기

### 1단계: Grafana 접속

```bash
# 새 터미널 창 열기
kubectl port-forward svc/grafana 3000:3000 -n agent-system
```

**브라우저에서 접속:**
```
http://localhost:3000
```

### 2단계: 로그인

- **Username**: `admin`
- **Password**: `admin123`

(처음 로그인 시 비밀번호 변경 프롬프트가 나올 수 있습니다. Skip 가능)

### 3단계: 데이터 소스 확인

**좌측 메뉴: ⚙️ Configuration → Data Sources**

**Prometheus** 데이터 소스 클릭

**Test 버튼 클릭:**
```
✅ Data source is working
```

### 4단계: 대시보드 열기

**좌측 메뉴: 📊 Dashboards → Browse**

**"API Performance Monitoring" 클릭**

다음 패널들이 표시됩니다:
- Request Rate (RPS)
- Response Time (P50, P95, P99)
- Error Rate
- Active Requests

### 5단계: 시간 범위 조정

**우측 상단:**
```
[Last 6 hours ▼] → Last 1 hour 선택
```

**자동 새로고침:**
```
[⏱️ Off ▼] → 5s 선택
```

---

## 첫 번째 모니터링

### 실습: 실시간 모니터링 체험

#### 준비

**터미널 1: Prometheus**
```bash
kubectl port-forward svc/prometheus 9090:9090 -n agent-system
```

**터미널 2: Grafana**
```bash
kubectl port-forward svc/grafana 3000:3000 -n agent-system
```

**터미널 3: Router Agent Port Forward**
```bash
kubectl port-forward svc/router-agent-svc 5000:5000 -n agent-system
```

#### 트래픽 생성

**터미널 4: 테스트 요청 실행**
```bash
# 20번 반복 요청
for i in {1..20}; do
  curl -s http://localhost:5000/health > /dev/null
  echo "Request $i sent at $(date +%H:%M:%S)"
  sleep 1
done
```

#### 모니터링

**브라우저 1: Prometheus (http://localhost:9090)**

쿼리 실행:
```promql
rate(router_requests_total[1m])
```

- Graph 탭 선택
- Auto-refresh 5s 설정
- 그래프가 실시간으로 증가하는 것 확인!

**브라우저 2: Grafana (http://localhost:3000)**

- API Performance Monitoring 대시보드
- Auto-refresh 5s 설정
- Request Rate 패널에서 증가 확인
- Active Requests 패널에서 실시간 변화 확인

---

## 실전 예제

### 예제 1: 처리 시간 분석

**목표**: 어떤 작업이 가장 오래 걸리는지 파악

**Prometheus 쿼리:**
```promql
# Intent 분류 평균 시간
rate(router_classification_duration_seconds_sum[5m]) /
rate(router_classification_duration_seconds_count[5m])

# SDB Agent 평균 처리 시간
rate(sdb_processing_duration_seconds_sum[5m]) /
rate(sdb_processing_duration_seconds_count[5m])
```

**결과 해석:**
- Intent 분류: 3초
- SDB Agent: 108초

→ **SDB Agent가 대부분의 시간을 차지** (LLM 호출 + Bitbucket API)

### 예제 2: 성공률 확인

**목표**: PR 생성 성공률 확인

**Prometheus 쿼리:**
```promql
sum(sdb_pr_created_total{status="success"}) /
sum(sdb_pr_created_total) * 100
```

**결과:**
```
100% (2/2 성공)
```

### 예제 3: 에러 모니터링

**목표**: 어떤 에러가 발생했는지 확인

**Prometheus 쿼리:**
```promql
sum by (error_type) (router_errors_total)
```

**Table 결과:**
```
router_errors_total{error_type="RateLimitError"} = 1
```

→ OpenAI Rate Limit 1건 발생

---

## 유용한 단축키

### Prometheus

| 단축키 | 기능 |
|--------|------|
| Ctrl/Cmd + Enter | 쿼리 실행 |
| Tab | 자동완성 |
| Shift + Enter | 새 줄 |

### Grafana

| 단축키 | 기능 |
|--------|------|
| d + k | 대시보드 검색 |
| d + h | 홈으로 |
| Ctrl/Cmd + S | 대시보드 저장 |
| e | 패널 편집 모드 |
| v | 패널 보기 모드 |
| ESC | 전체화면 종료 |

---

## 다음 단계

### 5분 완료! 🎉

축하합니다! 이제 기본적인 모니터링을 할 수 있습니다.

### 더 배우기

#### 초급 (완료 ✅)
- [x] Prometheus 접속
- [x] 기본 쿼리 실행
- [x] Grafana 대시보드 보기

#### 중급 (다음 학습)
1. [**PROMETHEUS_GUIDE.md**](PROMETHEUS_GUIDE.md)
   - PromQL 상세 문법
   - 집계 함수
   - Histogram 분석

2. [**GRAFANA_GUIDE.md**](GRAFANA_GUIDE.md)
   - 커스텀 패널 생성
   - 변수 사용
   - 알림 설정

3. [**PROMQL_QUERIES.md**](PROMQL_QUERIES.md)
   - 즉시 사용 가능한 쿼리 25개
   - 실전 예제

#### 고급 (심화 학습)
- 커스텀 대시보드 생성
- 복잡한 PromQL 쿼리
- 알림 채널 연동 (Slack)
- 성능 최적화

---

## 체크리스트

### 완료 확인

- [ ] Prometheus 접속 성공 (http://localhost:9090)
- [ ] Targets가 모두 UP 상태
- [ ] 첫 번째 쿼리 실행 성공
- [ ] Grafana 로그인 성공 (http://localhost:3000)
- [ ] 대시보드에서 데이터 확인
- [ ] 테스트 요청으로 실시간 모니터링 체험

모두 체크했다면 준비 완료! 🚀

---

## 문제 해결

### Prometheus에 접속 안 됨

```bash
# Port Forward 프로세스 확인
ps aux | grep "kubectl port-forward.*prometheus"

# 다시 시작
kubectl port-forward svc/prometheus 9090:9090 -n agent-system
```

### Targets가 DOWN 상태

```bash
# Pod 상태 확인
kubectl get pods -n agent-system -l app=router-agent

# Pod 로그 확인
kubectl logs -n agent-system -l app=router-agent --tail=50

# /metrics 엔드포인트 직접 테스트
kubectl exec -n agent-system deployment/router-agent -- curl localhost:5000/metrics
```

### Grafana 로그인 실패

기본 비밀번호:
- Username: `admin`
- Password: `admin123`

변경했다면:
```bash
# Grafana Secret 확인
kubectl get secret grafana-admin -n agent-system -o jsonpath='{.data.password}' | base64 -d
echo
```

### 메트릭이 안 보임

```bash
# Prometheus ConfigMap 확인
kubectl get configmap prometheus-config -n agent-system -o yaml

# Agent Pod annotations 확인
kubectl get pod -n agent-system -l app=router-agent -o yaml | grep -A 3 "prometheus.io"
```

---

## 다음 문서

- [Prometheus 상세 가이드](PROMETHEUS_GUIDE.md) - PromQL 마스터하기
- [Grafana 완전 정복](GRAFANA_GUIDE.md) - 대시보드 커스터마이징
- [PromQL 쿼리 모음](PROMQL_QUERIES.md) - 바로 사용 가능한 쿼리

---

**Happy Monitoring!** 📊
