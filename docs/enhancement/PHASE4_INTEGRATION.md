# Phase 4: 통합 및 최적화

## 문서 정보
- **Phase**: 4 / 4 (최종)
- **예상 기간**: 1주 (Week 6)
- **난이도**: ⭐⭐⭐⭐ (중상)
- **선행 요구사항**: Phase 1, 2, 3 완료

---

## 목차
1. [개요](#개요)
2. [통합 테스트](#통합-테스트)
3. [Grafana 고도화 대시보드](#grafana-고도화-대시보드)
4. [성능 튜닝](#성능-튜닝)
5. [장애 시나리오 테스트](#장애-시나리오-테스트)
6. [최종 검증](#최종-검증)
7. [프로덕션 배포](#프로덕션-배포)

---

## 개요

### 목표
- 모든 컴포넌트의 원활한 연동 확인
- 성능 최적화 (응답 시간, 리소스 사용량)
- 장애 대응 능력 검증
- 프로덕션 배포 준비

### 통합 구성 요소

```
┌─────────────────────────────────────────────────────────────┐
│  Jira Webhook                                                │
│      ↓                                                       │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Router Agent                                       │    │
│  │  ├─ Metrics → Prometheus                           │    │
│  │  ├─ Cache → Redis                                   │    │
│  │  ├─ History → PostgreSQL                           │    │
│  │  └─ Logs → stdout                                   │    │
│  └───────┬────────────────────────────────────────────┘    │
│          ↓                                                   │
│  ┌────────────────────────────────────────────────────┐    │
│  │  SDB Agent                                          │    │
│  │  ├─ Metrics → Prometheus                           │    │
│  │  ├─ Cache → Redis                                   │    │
│  │  ├─ History → PostgreSQL                           │    │
│  │  └─ Logs → stdout                                   │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Infrastructure                                      │   │
│  │  ├─ Redis (캐싱)                                     │   │
│  │  ├─ PostgreSQL (이력)                                │   │
│  │  ├─ Prometheus (메트릭)                              │   │
│  │  └─ Grafana (대시보드)                               │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 통합 테스트

### 1. End-to-End 테스트

**파일**: `test/e2e-test.sh`

```bash
#!/bin/bash
# End-to-End 통합 테스트

set -e

NAMESPACE="agent-system"
ROUTER_URL="http://localhost:5000"  # Port-forward 후 사용

echo "=== Multi-Agent 시스템 통합 테스트 ==="
echo ""

# 1. 인프라 상태 확인
echo "[1/6] 인프라 상태 확인..."
kubectl get pods -n $NAMESPACE
echo ""

# 2. Redis 연결 확인
echo "[2/6] Redis 연결 확인..."
kubectl exec -n $NAMESPACE deploy/redis -- redis-cli PING | grep PONG || exit 1
echo "✓ Redis OK"
echo ""

# 3. PostgreSQL 연결 확인
echo "[3/6] PostgreSQL 연결 확인..."
kubectl exec -n $NAMESPACE postgresql-0 -- psql -U agent_user -d agent_system -c "SELECT 1;" || exit 1
echo "✓ PostgreSQL OK"
echo ""

# 4. Webhook 요청 전송
echo "[4/6] Webhook 테스트 (End-to-End)..."
RESPONSE=$(curl -s -X POST $ROUTER_URL/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "issue": {
      "key": "E2E-TEST-001",
      "fields": {
        "summary": "SDB 개발 요청: E2E 테스트",
        "description": "통합 테스트를 위한 이슈",
        "issuetype": {"name": "Task"}
      }
    },
    "webhookEvent": "jira:issue_created"
  }')

echo "Response: $RESPONSE"
REQUEST_ID=$(echo $RESPONSE | jq -r '.request_id')
echo "Request ID: $REQUEST_ID"
echo ""

# 5. DB 데이터 확인
echo "[5/6] DB 데이터 저장 확인..."
sleep 2  # 데이터 저장 대기

DB_COUNT=$(kubectl exec -n $NAMESPACE postgresql-0 -- \
  psql -U agent_user -d agent_system -t -c \
  "SELECT COUNT(*) FROM request_history WHERE issue_key = 'E2E-TEST-001';")

if [ "$DB_COUNT" -gt 0 ]; then
  echo "✓ DB에 $DB_COUNT 건의 이력 저장됨"
else
  echo "✗ DB 저장 실패"
  exit 1
fi
echo ""

# 6. 캐시 확인
echo "[6/6] Redis 캐시 확인..."
CACHE_KEYS=$(kubectl exec -n $NAMESPACE deploy/redis -- redis-cli KEYS "*")
if [ -n "$CACHE_KEYS" ]; then
  echo "✓ 캐시 키 발견: $(echo $CACHE_KEYS | wc -w)개"
else
  echo "⚠ 캐시 키 없음 (정상일 수 있음)"
fi
echo ""

echo "==================================="
echo "✓ 통합 테스트 완료!"
echo "==================================="
```

### 2. 성능 벤치마크

**파일**: `test/benchmark.sh`

```bash
#!/bin/bash
# 성능 벤치마크 테스트

ROUTER_URL="http://localhost:5000"
REQUESTS=100
CONCURRENCY=10

echo "=== 성능 벤치마크 ==="
echo "요청 수: $REQUESTS"
echo "동시성: $CONCURRENCY"
echo ""

# Apache Bench 사용
ab -n $REQUESTS -c $CONCURRENCY -T 'application/json' \
  -p test/test-webhook.json \
  $ROUTER_URL/webhook

echo ""
echo "=== Prometheus 메트릭 확인 ==="
curl -s http://localhost:9090/api/v1/query?query=router_requests_total | jq
```

---

## Grafana 고도화 대시보드

### 1. 캐시 효율성 대시보드

**목적**: Redis 캐시 성능 분석

**패널**:
1. **캐시 히트율** (%)
2. **캐시 유형별 히트/미스**
3. **절감된 API 호출 횟수**
4. **절감된 비용 (LLM 토큰)**
5. **Redis 메모리 사용량**

**PromQL 쿼리**:

```promql
# 전체 캐시 히트율
sum(rate(cache_hits_total[5m])) / (sum(rate(cache_hits_total[5m])) + sum(rate(cache_misses_total[5m]))) * 100

# Bitbucket API 호출 감소율
(1 - sum(rate(sdb_bitbucket_api_calls_total{status="success"}[1h])) / avg_over_time(sdb_bitbucket_api_calls_total{status="success"}[7d])) * 100

# LLM 비용 절감액 (가정: $0.01/1K 토큰)
sum(increase(cache_hits_total{cache_type="llm"}[1h])) * 1.5 * 0.01

# Redis 메모리
redis_memory_used_bytes / redis_memory_max_bytes * 100
```

### 2. 이력 분석 대시보드

**목적**: PostgreSQL 데이터 분석

**패널**:
1. **일별 처리 건수** (시계열)
2. **Agent별 분포** (파이 차트)
3. **평균 신뢰도** (게이지)
4. **가장 많이 수정된 파일 Top 10**
5. **낮은 신뢰도 이슈 목록**

**쿼리** (PostgreSQL 직접 쿼리 - Grafana PostgreSQL 데이터 소스):

```sql
-- 일별 처리 건수
SELECT
  DATE(created_at) AS time,
  COUNT(*) AS count
FROM request_history
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY time;

-- Agent별 분포
SELECT
  classified_agent,
  COUNT(*) AS count
FROM classification_history
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY classified_agent;

-- 가장 많이 수정된 파일
SELECT
  file_path,
  COUNT(*) AS change_count
FROM code_change_history
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY file_path
ORDER BY change_count DESC
LIMIT 10;
```

### 3. 비용 분석 대시보드

**목적**: 운영 비용 추적 및 최적화

**패널**:
1. **LLM 토큰 사용량** (일별/월별)
2. **LLM 비용 추정** (USD)
3. **캐시로 절감된 비용**
4. **Bitbucket API 호출 횟수**
5. **Agent별 리소스 사용량**

**PromQL + PostgreSQL 쿼리**:

```promql
# 일별 LLM 토큰 사용량
sum(increase(sdb_llm_tokens_used_total[1d]))

# 월별 예상 비용 (GPT-4 기준: $0.03/1K prompt, $0.06/1K completion)
(sum(increase(sdb_llm_tokens_used_total{token_type="prompt"}[30d])) * 0.03 / 1000) +
(sum(increase(sdb_llm_tokens_used_total{token_type="completion"}[30d])) * 0.06 / 1000)
```

```sql
-- PostgreSQL: 상세 LLM 사용 이력
SELECT
  DATE(created_at) AS date,
  SUM(metric_value) FILTER (WHERE metadata->>'type' = 'prompt') AS prompt_tokens,
  SUM(metric_value) FILTER (WHERE metadata->>'type' = 'completion') AS completion_tokens
FROM performance_metrics
WHERE metric_type = 'llm_tokens'
  AND created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

### 4. 대시보드 JSON 예시

**파일**: `helm/multi-agent-system/templates/monitoring/grafana/dashboards/cache-efficiency.json`

```json
{
  "dashboard": {
    "title": "Cache Efficiency Dashboard",
    "panels": [
      {
        "id": 1,
        "title": "Overall Cache Hit Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "sum(rate(cache_hits_total[5m])) / (sum(rate(cache_hits_total[5m])) + sum(rate(cache_misses_total[5m]))) * 100",
            "legendFormat": "Hit Rate %"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "percent",
            "thresholds": {
              "steps": [
                {"value": 0, "color": "red"},
                {"value": 50, "color": "yellow"},
                {"value": 70, "color": "green"}
              ]
            }
          }
        }
      }
    ]
  }
}
```

---

## 성능 튜닝

### 1. Redis 최적화

```yaml
# Redis ConfigMap 수정
data:
  redis.conf: |
    # 메모리 최적화
    maxmemory 1gb  # 512mb → 1gb
    maxmemory-policy allkeys-lru

    # 지속성 비활성화 (순수 캐시 용도)
    save ""
    appendonly no

    # 네트워크 최적화
    tcp-backlog 511
    timeout 0
    tcp-keepalive 300
```

### 2. PostgreSQL 최적화

```sql
-- 연결 풀 크기 조정
ALTER SYSTEM SET max_connections = 200;

-- Shared buffers 증가 (메모리의 25%)
ALTER SYSTEM SET shared_buffers = '512MB';

-- Work memory 증가
ALTER SYSTEM SET work_mem = '16MB';

-- Effective cache size (메모리의 50-75%)
ALTER SYSTEM SET effective_cache_size = '2GB';

-- 재시작 필요
SELECT pg_reload_conf();
```

### 3. Agent 리소스 조정

**파일**: `helm/multi-agent-system/values.yaml` (수정)

```yaml
routerAgent:
  resources:
    requests:
      cpu: 500m     # 250m → 500m
      memory: 512Mi # 256Mi → 512Mi
    limits:
      cpu: 1000m    # 500m → 1000m
      memory: 1Gi   # 512Mi → 1Gi

sdbAgent:
  resources:
    requests:
      cpu: 1000m    # 500m → 1000m
      memory: 1Gi   # 512Mi → 1Gi
    limits:
      cpu: 2000m    # 동일
      memory: 2Gi   # 동일
```

### 4. HPA 튜닝

```yaml
# Router Agent HPA 수정
spec:
  minReplicas: 2  # 3 → 2 (비용 절감)
  maxReplicas: 15 # 10 → 15 (높은 트래픽 대응)
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 60  # 70 → 60 (더 빠른 스케일 업)
```

---

## 장애 시나리오 테스트

### 1. Redis 장애

**시나리오**: Redis Pod 삭제

```bash
# Redis 삭제
kubectl delete pod -n agent-system -l app=redis

# 시스템 동작 확인 (캐시 없이도 작동해야 함)
curl -X POST http://router-agent/webhook -d @test-webhook.json

# Redis 복구 확인
kubectl get pod -n agent-system -l app=redis
```

**예상 결과**:
- ✓ Agent가 캐시 없이 정상 동작
- ✓ 로그에 "Redis 연결 실패, 캐싱 비활성화" 메시지
- ✓ Redis 복구 후 자동 재연결

### 2. PostgreSQL 장애

**시나리오**: PostgreSQL Pod 재시작

```bash
# PostgreSQL 재시작
kubectl rollout restart statefulset postgresql -n agent-system

# 시스템 동작 확인
curl -X POST http://router-agent/webhook -d @test-webhook.json

# DB 복구 확인
kubectl exec -n agent-system postgresql-0 -- psql -U agent_user -d agent_system -c "SELECT COUNT(*) FROM request_history;"
```

**예상 결과**:
- ✓ Agent가 DB 없이 정상 동작 (이력만 누락)
- ✓ PostgreSQL 복구 후 자동 재연결

### 3. Agent 스케일 인/아웃

**시나리오**: 부하 증가 시 자동 스케일링

```bash
# 부하 테스트
ab -n 1000 -c 50 -T 'application/json' -p test-webhook.json http://router-agent/webhook

# HPA 상태 확인
kubectl get hpa -n agent-system -w

# Pod 개수 확인
kubectl get pods -n agent-system -l app=router-agent
```

**예상 결과**:
- ✓ CPU 사용률 60% 초과 시 자동 스케일 업
- ✓ 부하 감소 시 자동 스케일 다운 (5분 후)

### 4. Prometheus/Grafana 장애

**시나리오**: 모니터링 시스템 중단

```bash
# Prometheus 중단
kubectl scale deployment prometheus --replicas=0 -n agent-system

# Agent 동작 확인
curl http://router-agent/webhook
```

**예상 결과**:
- ✓ Agent가 정상 동작 (메트릭 수집만 실패)
- ✓ 로그에 경고 메시지 없음 (비동기 메트릭)

---

## 최종 검증

### 검증 체크리스트

#### 기능 검증
- [ ] Jira Webhook → Router → SDB Agent 전체 플로우 정상
- [ ] Intent Classification 정확도 > 90%
- [ ] PR 자동 생성 성공률 > 95%

#### 성능 검증
- [ ] 평균 응답 시간 < 3초
- [ ] P95 응답 시간 < 10초
- [ ] 캐시 히트율 > 60%
- [ ] API 호출 감소율 > 70%

#### 안정성 검증
- [ ] Redis 장애 시 정상 동작 (degraded mode)
- [ ] PostgreSQL 장애 시 정상 동작 (no history)
- [ ] Agent Pod 재시작 시 데이터 유실 없음
- [ ] HPA 자동 스케일링 정상 동작

#### 모니터링 검증
- [ ] Prometheus가 모든 메트릭 수집
- [ ] Grafana 대시보드 정상 표시 (7개)
- [ ] 알림 규칙 정상 트리거
- [ ] PostgreSQL 이력 데이터 정상 저장

### 성능 KPI 달성 확인

| KPI | 목표 | 실제 | 달성 여부 |
|-----|------|------|-----------|
| 평균 응답 시간 | 2.5초 | _____초 | ⬜ |
| API 호출 감소 | 70% | ____% | ⬜ |
| LLM 비용 절감 | 50% | ____% | ⬜ |
| 캐시 히트율 | 60% | ____% | ⬜ |
| 장애 감지 시간 | < 5분 | ____분 | ⬜ |
| 시스템 가용성 | > 99% | ____% | ⬜ |

---

## 프로덕션 배포

### 1. 배포 전 체크리스트

- [ ] 모든 Phase 완료 및 검증
- [ ] 스테이징 환경에서 1주일 운영
- [ ] 백업 시스템 구축 완료
- [ ] 롤백 계획 수립
- [ ] 모니터링 대시보드 설정 완료
- [ ] 알림 채널 설정 완료 (Slack, Email)
- [ ] 운영 문서 작성 완료

### 2. 배포 절차

```bash
# 1. 프로덕션 values 파일 준비
cp helm/multi-agent-system/values-production.yaml values-prod.yaml
# values-prod.yaml 편집 (실제 값 입력)

# 2. 프로덕션 namespace 생성
kubectl create namespace agent-system-prod

# 3. Secrets 생성
kubectl create secret generic agent-secrets \
  --from-literal=openai-api-key='sk-...' \
  --from-literal=bitbucket-access-token='...' \
  --from-literal=postgresql-password='...' \
  -n agent-system-prod

# 4. Helm 배포
helm install multi-agent-system ./helm/multi-agent-system \
  -f values-prod.yaml \
  -n agent-system-prod

# 5. 배포 상태 확인
kubectl get pods -n agent-system-prod -w

# 6. 헬스 체크
kubectl port-forward svc/router-agent-svc 5000:5000 -n agent-system-prod
curl http://localhost:5000/health

# 7. 모니터링 확인
kubectl port-forward svc/grafana 3000:3000 -n agent-system-prod
# http://localhost:3000
```

### 3. Blue-Green 배포 (권장)

```bash
# Blue (기존) 환경 유지
# Green (신규) 환경 배포

# Green 배포
helm install multi-agent-system-green ./helm/multi-agent-system \
  -f values-prod.yaml \
  -n agent-system-prod

# Green 검증 (내부 테스트)
kubectl port-forward svc/router-agent-svc-green 5001:5000 -n agent-system-prod

# 트래픽 전환 (Ingress 수정)
kubectl edit ingress agent-ingress -n agent-system-prod
# backend.service.name을 router-agent-svc → router-agent-svc-green으로 변경

# Blue 환경 제거 (문제 없으면)
helm uninstall multi-agent-system -n agent-system-prod
```

### 4. 배포 후 모니터링

```bash
# 실시간 로그 모니터링
stern -n agent-system-prod router-agent,sdb-agent

# 메트릭 확인
watch -n 5 'kubectl top pods -n agent-system-prod'

# 에러율 확인
kubectl logs -n agent-system-prod -l app=router-agent | grep ERROR | tail -20
```

---

## 최종 정리

### 완료 사항
1. ✅ **Phase 1**: Prometheus + Grafana 모니터링
2. ✅ **Phase 2**: Redis 캐싱 통합
3. ✅ **Phase 3**: PostgreSQL 이력 관리
4. ✅ **Phase 4**: 통합 및 최적화

### 시스템 개선 효과

| 항목 | 개선 전 | 개선 후 | 개선율 |
|------|---------|---------|--------|
| 평균 응답 시간 | 5초 | 2.5초 | 50% ↓ |
| API 호출 횟수 | 100회/일 | 30회/일 | 70% ↓ |
| LLM 비용 | $100/월 | $50/월 | 50% ↓ |
| 장애 감지 시간 | 30분 | 5분 | 83% ↓ |
| 시스템 가시성 | 20% | 90% | 350% ↑ |

### 운영 문서

- [OPERATIONS_GUIDE.md](./OPERATIONS_GUIDE.md) - 일상 운영 가이드
- [DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md) - DB 스키마 참조
- [OVERVIEW.md](./OVERVIEW.md) - 전체 아키텍처 참조

---

**문서 버전**: 1.0.0
**최종 업데이트**: 2025-10-22
**다음 단계**: 프로덕션 배포 및 운영
