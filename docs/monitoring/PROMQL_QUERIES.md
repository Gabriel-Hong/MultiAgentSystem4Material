# PromQL 쿼리 모음

Multi-Agent 시스템에서 바로 사용할 수 있는 유용한 PromQL 쿼리 모음입니다.

## 📋 목차

1. [성능 메트릭](#성능-메트릭)
2. [비즈니스 메트릭](#비즈니스-메트릭)
3. [에러 모니터링](#에러-모니터링)
4. [시스템 리소스](#시스템-리소스)
5. [트렌드 분석](#트렌드-분석)
6. [고급 쿼리](#고급-쿼리)

---

## 성능 메트릭

### 1. 초당 요청 수 (RPS - Requests Per Second)

```promql
sum(rate(router_requests_total[1m]))
```

**용도**: 시스템의 전체 처리량 모니터링
**단위**: req/s
**알림 기준**: < 0.1 (너무 적음) 또는 > 10 (과부하)

### 2. 엔드포인트별 요청 수

```promql
sum by (endpoint) (router_requests_total)
```

**용도**: 어떤 엔드포인트가 가장 많이 호출되는지 파악
**Grafana**: Pie chart 또는 Bar gauge 사용

### 3. 성공률 (%)

```promql
sum(router_requests_total{status="success"}) /
sum(router_requests_total) * 100
```

**용도**: 전체 요청 중 성공한 비율
**목표**: > 95%
**알림 기준**: < 90%

### 4. 평균 응답 시간

```promql
rate(router_classification_duration_seconds_sum[5m]) /
rate(router_classification_duration_seconds_count[5m])
```

**용도**: Intent 분류 평균 소요 시간
**단위**: 초 (seconds)
**목표**: < 3초

### 5. 응답 시간 백분위수 (P50)

```promql
histogram_quantile(0.50,
  rate(router_classification_duration_seconds_bucket[5m])
)
```

**용도**: 50%의 요청이 이 시간 이내 완료
**단위**: 초
**의미**: 중앙값

### 6. 응답 시간 백분위수 (P95)

```promql
histogram_quantile(0.95,
  rate(router_classification_duration_seconds_bucket[5m])
)
```

**용도**: 95%의 요청이 이 시간 이내 완료
**목표**: < 10초
**알림 기준**: > 15초

### 7. 응답 시간 백분위수 (P99)

```promql
histogram_quantile(0.99,
  rate(router_classification_duration_seconds_bucket[5m])
)
```

**용도**: 거의 모든 요청(99%)의 응답 시간
**목표**: < 20초
**의미**: 최악의 경우에도 이 정도 시간

### 8. 메서드별 요청 분포

```promql
sum by (method) (router_requests_total)
```

**용도**: HTTP 메서드별 분포
**예상 결과**: POST가 대부분

### 9. 상태별 요청 분포

```promql
sum by (status) (router_requests_total)
```

**용도**: success/error 비율 시각화
**Grafana**: Pie chart 추천

### 10. 시간당 처리량

```promql
sum(rate(router_requests_total[1h])) * 3600
```

**용도**: 시간당 처리되는 요청 수
**단위**: requests/hour

---

## 비즈니스 메트릭

### 11. Agent별 호출 횟수

```promql
sum by (agent) (router_agent_calls_total)
```

**용도**: 어떤 Agent가 가장 많이 사용되는지
**Grafana**: Pie chart 또는 Bar gauge

### 12. SDB Agent 호출 비율

```promql
sum(router_agent_calls_total{agent="sdb-agent"}) /
sum(router_agent_calls_total) * 100
```

**용도**: 전체 호출 중 SDB Agent 비율
**예상**: 50-80%

### 13. Intent 분류 신뢰도 평균

```promql
router_classification_confidence_sum /
router_classification_confidence_count
```

**용도**: LLM 분류의 평균 신뢰도
**단위**: 0.0-1.0
**목표**: > 0.7 (70%)
**알림**: < 0.5 (불확실한 분류 많음)

### 14. PR 생성 성공률

```promql
sum(sdb_pr_created_total{status="success"}) /
sum(sdb_pr_created_total) * 100
```

**용도**: PR 생성 작업 성공률
**목표**: > 95%
**중요**: 낮으면 Bitbucket 연동 문제 의심

### 15. LLM 토큰 사용량 (시간당)

```promql
sum(rate(sdb_llm_tokens_used_total[1h])) * 3600
```

**용도**: 비용 추정 및 사용량 모니터링
**단위**: tokens/hour
**비용 계산**: tokens × 가격

### 16. LLM 토큰 사용량 (타입별)

```promql
sum by (token_type) (rate(sdb_llm_tokens_used_total[1h])) * 3600
```

**용도**: prompt vs completion 토큰 비교
**Grafana**: Stacked time series

### 17. Bitbucket API 호출 성공률

```promql
sum(sdb_bitbucket_api_calls_total{status="success"}) /
sum(sdb_bitbucket_api_calls_total) * 100
```

**용도**: Bitbucket 연동 안정성
**목표**: > 99%
**알림**: < 95%

### 18. Bitbucket API 호출 타입별 분포

```promql
sum by (api_type) (sdb_bitbucket_api_calls_total)
```

**용도**: get_file, create_pr 등 어떤 API를 많이 호출하는지
**Grafana**: Bar gauge

### 19. 파일 수정 건수 (일일)

```promql
sum(increase(sdb_files_modified_total[1d]))
```

**용도**: 하루에 몇 개 파일을 수정했는지
**단위**: files/day

### 20. SDB Agent 평균 처리 시간

```promql
rate(sdb_processing_duration_seconds_sum[5m]) /
rate(sdb_processing_duration_seconds_count[5m])
```

**용도**: SDB Agent 전체 처리 시간
**단위**: 초
**참고**: 평균 100초 이상 (LLM + Bitbucket)

---

## 에러 모니터링

### 21. 총 에러 수

```promql
sum(router_errors_total)
```

**용도**: 시스템 시작 후 누적 에러
**목표**: 최소화

### 22. 에러 타입별 분포

```promql
sum by (error_type) (router_errors_total)
```

**용도**: 어떤 종류의 에러가 많은지
**예시**: RateLimitError, TimeoutError, ConnectionError
**Grafana**: Table 또는 Bar gauge

### 23. 에러 발생률 (%)

```promql
sum(rate(router_errors_total[5m])) /
sum(rate(router_requests_total[5m])) * 100
```

**용도**: 요청 대비 에러 비율
**목표**: < 1%
**알림**: > 5%

### 24. 최근 5분간 에러 증가량

```promql
increase(router_errors_total[5m])
```

**용도**: 급격한 에러 증가 감지
**알림**: > 10 (5분에 10개 이상)

### 25. Agent별 에러 발생

```promql
sum by (agent) (router_errors_total)
```

**용도**: 어느 Agent/컴포넌트에서 에러가 많은지
**Grafana**: Bar gauge

### 26. 시간당 에러 발생 추이

```promql
sum(rate(router_errors_total[1h]))
```

**용도**: 에러 발생 트렌드
**Grafana**: Time series

### 27. SDB Agent 에러 비율

```promql
sum(sdb_errors_total) /
sum(sdb_pr_created_total) * 100
```

**용도**: SDB 작업 중 에러 비율

---

## 시스템 리소스

### 28. 메모리 사용량 (MB)

```promql
process_resident_memory_bytes / 1024 / 1024
```

**용도**: Agent 프로세스 메모리 사용량
**단위**: MiB
**알림**: > 500MB (Router), > 1GB (SDB)

### 29. CPU 사용 시간 (초당)

```promql
rate(process_cpu_seconds_total[1m])
```

**용도**: CPU 사용률
**단위**: cores
**의미**: 0.5 = 50% CPU 사용

### 30. 열린 파일 디스크립터

```promql
process_open_fds
```

**용도**: 파일/소켓 핸들 개수
**알림**: > 100 (리소스 릭 의심)

### 31. 최대 파일 디스크립터

```promql
process_max_fds
```

**용도**: 시스템 제한
**확인**: open_fds / max_fds < 0.8

### 32. Python GC 실행 횟수

```promql
rate(python_gc_collections_total[5m])
```

**용도**: 메모리 관리 상태
**높으면**: 메모리 압박

### 33. 활성 요청 수

```promql
router_active_requests
```

**용도**: 현재 처리 중인 요청
**알림**: > 10 (병목 의심)

### 34. 활성 작업 수 (SDB)

```promql
sdb_active_tasks
```

**용도**: SDB Agent 현재 처리 중인 작업
**정상**: 0-2

### 35. 전체 활성 작업

```promql
router_active_requests + sdb_active_tasks
```

**용도**: 시스템 전체 부하
**알림**: > 15

---

## 트렌드 분석

### 36. 1시간 전과 현재 요청 수 비교

```promql
sum(router_requests_total) -
sum(router_requests_total offset 1h)
```

**용도**: 지난 1시간 동안 처리된 요청 수
**단위**: 절대 개수

### 37. 지난 주 같은 시간과 비교

```promql
sum(rate(router_requests_total[5m])) /
sum(rate(router_requests_total[5m] offset 1w))
```

**용도**: 주간 패턴 분석
**의미**: 1.5 = 지난주보다 50% 증가

### 38. 일일 요청 증가량

```promql
increase(router_requests_total[1d])
```

**용도**: 하루 동안 처리된 요청 수
**단위**: requests/day

### 39. 요청 증가 속도

```promql
deriv(router_requests_total[1h])
```

**용도**: 요청 증가 가속도
**의미**: 양수면 증가, 음수면 감소

### 40. 최근 증가/감소 추세

```promql
predict_linear(router_requests_total[1h], 3600)
```

**용도**: 1시간 데이터로 1시간 후 예측

---

## 고급 쿼리

### 41. Agent 호출 성공률 (Agent별)

```promql
sum by (agent) (router_agent_calls_total{status="success"}) /
sum by (agent) (router_agent_calls_total) * 100
```

**용도**: 각 Agent별 성공률

### 42. 평균 신뢰도가 낮은 요청 비율

```promql
count(router_classification_confidence_bucket{le="0.5"}) /
count(router_classification_confidence_bucket{le="+Inf"}) * 100
```

**용도**: 불확실한 분류 비율
**목표**: < 10%

### 43. Bitbucket API 응답 시간 (예상)

```promql
rate(sdb_processing_duration_seconds_sum[5m]) /
rate(sdb_processing_duration_seconds_count[5m]) -
rate(sdb_llm_requests_total[5m]) * 5
```

**용도**: LLM 시간 제외한 Bitbucket 시간
**참고**: 대략적인 추정

### 44. LLM 호출 실패율

```promql
sum(sdb_llm_requests_total{status="error"}) /
sum(sdb_llm_requests_total) * 100
```

**용도**: LLM API 안정성
**목표**: < 1%

### 45. 요청당 평균 LLM 토큰

```promql
sum(sdb_llm_tokens_used_total) /
sum(router_requests_total{endpoint="webhook"})
```

**용도**: 요청 1건당 사용하는 토큰 수
**단위**: tokens/request
**비용 예측**: 이 값 × 예상 요청 수 × 토큰 가격

### 46. PR 생성 성공 vs 실패 비율

```promql
sum(sdb_pr_created_total{status="success"}) /
sum(sdb_pr_created_total{status="failed"})
```

**용도**: 성공/실패 비율
**목표**: > 10 (성공이 실패의 10배 이상)

### 47. 요청 처리 전체 소요 시간 (P95)

```promql
histogram_quantile(0.95,
  rate(router_classification_duration_seconds_bucket[5m])
) +
histogram_quantile(0.95,
  rate(sdb_processing_duration_seconds_bucket[5m])
)
```

**용도**: 분류 + 처리 전체 시간
**단위**: 초

### 48. 에러 없이 처리된 비율

```promql
(sum(router_requests_total) - sum(router_errors_total)) /
sum(router_requests_total) * 100
```

**용도**: 전체 성공률 (에러 포함)
**목표**: > 95%

### 49. 최근 10분간 가장 느린 P99

```promql
max_over_time(
  histogram_quantile(0.99,
    rate(router_classification_duration_seconds_bucket[1m])
  )[10m:]
)
```

**용도**: 최근 10분 중 가장 느렸던 순간

### 50. Agent별 평균 처리 시간

```promql
sum by (agent) (
  rate(router_agent_call_duration_seconds_sum[5m])
) /
sum by (agent) (
  rate(router_agent_call_duration_seconds_count[5m])
)
```

**용도**: Agent별 성능 비교
**단위**: 초

---

## 사용 팁

### Grafana에서 사용하기

1. **패널 추가**
   - Dashboard → Add panel
   - Query에 위 쿼리 복사

2. **Legend 설정**
   - Legend: `{{label_name}}`
   - 예: `{{endpoint}}`, `{{agent}}`

3. **Unit 설정**
   - 시간: `seconds (s)`
   - 비율: `percent (0-100)`
   - 개수: `short`
   - 메모리: `bytes (IEC)`

### Prometheus에서 테스트

1. **Graph 페이지**에서 쿼리 입력
2. **Execute** 클릭
3. **Table/Graph** 전환하며 확인

### 알림 규칙 예시

```yaml
- alert: HighErrorRate
  expr: sum(rate(router_errors_total[5m])) / sum(rate(router_requests_total[5m])) * 100 > 5
  for: 2m
  labels:
    severity: warning
  annotations:
    summary: "에러율이 5% 초과"
    description: "현재 에러율: {{ $value }}%"
```

---

## 다음 단계

- [Prometheus 완전 가이드](PROMETHEUS_GUIDE.md) - PromQL 문법 자세히
- [Grafana 사용법](GRAFANA_GUIDE.md) - 대시보드 커스터마이징
- [빠른 시작](MONITORING_QUICKSTART.md) - 5분 튜토리얼

---

**쿼리를 복사해서 바로 사용하세요!** 📊
