# Monitoring 문서

Multi-Agent 시스템의 Prometheus 및 Grafana 모니터링 가이드입니다.

## 📚 문서 목록

### 빠른 시작
- [**MONITORING_QUICKSTART.md**](MONITORING_QUICKSTART.md) - 5분 안에 모니터링 시작하기

### 상세 가이드
- [**PROMETHEUS_GUIDE.md**](PROMETHEUS_GUIDE.md) - Prometheus 사용법 완전 가이드
- [**GRAFANA_GUIDE.md**](GRAFANA_GUIDE.md) - Grafana 대시보드 사용법
- [**PROMQL_QUERIES.md**](PROMQL_QUERIES.md) - 유용한 PromQL 쿼리 모음

## 🎯 무엇을 모니터링하나요?

### Router Agent 메트릭
- 총 요청 수 (`router_requests_total`)
- Intent 분류 시간 (`router_classification_duration_seconds`)
- Agent 호출 횟수 (`router_agent_calls_total`)
- 에러 발생 (`router_errors_total`)
- 활성 요청 수 (`router_active_requests`)
- 분류 신뢰도 (`router_classification_confidence`)

### SDB Agent 메트릭
- 처리 시간 (`sdb_processing_duration_seconds`)
- Bitbucket API 호출 (`sdb_bitbucket_api_calls_total`)
- LLM 요청 수 (`sdb_llm_requests_total`)
- LLM 토큰 사용량 (`sdb_llm_tokens_used_total`)
- PR 생성 성공/실패 (`sdb_pr_created_total`)
- 수정된 파일 수 (`sdb_files_modified_total`)

## 🚀 빠른 시작

### 1. Port Forward 설정

```bash
# Prometheus
kubectl port-forward svc/prometheus 9090:9090 -n agent-system

# Grafana
kubectl port-forward svc/grafana 3000:3000 -n agent-system
```

### 2. 접속

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin / admin123)

### 3. 첫 번째 쿼리 실행

Prometheus에서:
```promql
router_requests_total
```

## 📊 주요 대시보드

Grafana에서 다음 대시보드를 확인할 수 있습니다:

1. **API Performance Monitoring**
   - 요청 처리량 (RPS)
   - 응답 시간 (P50, P95, P99)
   - 에러율
   - 활성 요청 수

2. **Business Metrics**
   - Agent별 호출 분포
   - PR 생성 성공률
   - LLM 토큰 사용량
   - 처리 시간 추이

3. **Error Tracking**
   - 에러 발생 추이
   - 에러 타입별 분포
   - Agent별 에러율

4. **System Resources Monitoring**
   - CPU 사용률
   - 메모리 사용량
   - 네트워크 I/O
   - Python GC 통계

## 🔍 실전 사용 예시

### 성능 저하 분석

**문제**: 시스템이 느려졌다는 보고

**조사 순서**:
1. Prometheus에서 응답 시간 확인
   ```promql
   histogram_quantile(0.95, rate(router_classification_duration_seconds_bucket[5m]))
   ```

2. 어느 구간이 느린지 파악
   - Intent 분류 시간
   - SDB Agent 처리 시간
   - LLM 호출 시간

3. 로그 확인
   ```bash
   kubectl logs -n agent-system -l app=router-agent --tail=100
   ```

### 에러 급증 대응

**알림**: 에러율이 10% 초과

**대응**:
1. 에러 타입 확인
   ```promql
   sum by (error_type) (router_errors_total)
   ```

2. 발생 시점 파악 (Grafana Graph)

3. 로그에서 상세 정보 추출
   ```bash
   kubectl logs -n agent-system -l app=router-agent | grep ERROR
   ```

## 📖 학습 경로

### 초급 (1-2일)
1. [빠른 시작 가이드](MONITORING_QUICKSTART.md) 완료
2. Prometheus UI에서 기본 쿼리 실행
3. Grafana 대시보드 둘러보기

### 중급 (1주)
1. [PromQL 쿼리 모음](PROMQL_QUERIES.md)에서 주요 쿼리 학습
2. Grafana에서 커스텀 패널 생성
3. 알림 규칙 이해

### 고급 (2-4주)
1. 복잡한 PromQL 쿼리 작성
2. 커스텀 대시보드 생성
3. 알림 채널 연동 (Slack, Email)
4. 성능 최적화 및 트러블슈팅

## 🔗 관련 문서

### 프로젝트 문서
- [MONITORING_IMPLEMENTATION.md](../../MONITORING_IMPLEMENTATION.md) - 구현 완료 내역
- [PHASE1_MONITORING.md](../enhancement/PHASE1_MONITORING.md) - 모니터링 설계 문서

### 외부 리소스
- [Prometheus 공식 문서](https://prometheus.io/docs/)
- [Grafana 튜토리얼](https://grafana.com/tutorials/)
- [PromQL 치트시트](https://promlabs.com/promql-cheat-sheet/)

## ❓ FAQ

**Q: Prometheus와 Grafana의 차이는?**
A: Prometheus는 메트릭을 수집하고 저장하는 시스템이고, Grafana는 수집된 메트릭을 시각화하는 대시보드 도구입니다.

**Q: 메트릭이 안 보여요**
A: Status → Targets에서 Agent Pod가 UP 상태인지 확인하세요. DOWN이면 Pod 로그를 확인하세요.

**Q: 그래프가 이상해요**
A: Counter 메트릭은 계속 증가하므로 `rate()` 함수를 사용해야 합니다.

**Q: 대시보드를 수정했는데 사라졌어요**
A: Dashboard 우측 상단의 "Save dashboard" 버튼을 클릭해야 저장됩니다.

**Q: 알림이 안 와요**
A: Prometheus에서 Alert Rules가 Firing 상태인지, Alertmanager가 설정되어 있는지 확인하세요.

## 🆘 도움말

문제가 있거나 질문이 있으면:
1. 이 문서들을 먼저 확인
2. Prometheus/Grafana 로그 확인
3. GitHub Issues에 문의

---

**즐거운 모니터링 되세요!** 📊
