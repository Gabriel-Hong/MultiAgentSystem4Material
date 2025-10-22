# 운영 가이드

## 문서 정보
- **버전**: 1.0.0
- **작성일**: 2025-10-22
- **대상**: 시스템 운영자, DevOps 엔지니어

---

## 목차
1. [일상 운영](#일상-운영)
2. [모니터링](#모니터링)
3. [알림 대응](#알림-대응)
4. [트러블슈팅](#트러블슈팅)
5. [백업 및 복구](#백업-및-복구)
6. [스케일링](#스케일링)
7. [업데이트 및 배포](#업데이트-및-배포)
8. [보안](#보안)

---

## 일상 운영

### 매일 체크리스트

```bash
#!/bin/bash
# daily-check.sh - 매일 실행할 체크 스크립트

NAMESPACE="agent-system"

echo "=== 일일 시스템 체크 ==="
echo "날짜: $(date)"
echo ""

# 1. Pod 상태
echo "[1/7] Pod 상태 확인"
kubectl get pods -n $NAMESPACE
echo ""

# 2. HPA 상태
echo "[2/7] Auto-scaling 상태"
kubectl get hpa -n $NAMESPACE
echo ""

# 3. 리소스 사용량
echo "[3/7] 리소스 사용량"
kubectl top pods -n $NAMESPACE
echo ""

# 4. 에러 로그 확인 (최근 1시간)
echo "[4/7] 최근 에러 로그"
kubectl logs -n $NAMESPACE -l app=router-agent --since=1h | grep -i error | tail -10
kubectl logs -n $NAMESPACE -l app=sdb-agent --since=1h | grep -i error | tail -10
echo ""

# 5. Redis 상태
echo "[5/7] Redis 상태"
kubectl exec -n $NAMESPACE deploy/redis -- redis-cli INFO stats | grep -E "keyspace_hits|keyspace_misses|used_memory_human"
echo ""

# 6. PostgreSQL 상태
echo "[6/7] PostgreSQL 상태"
kubectl exec -n $NAMESPACE postgresql-0 -- psql -U agent_user -d agent_system -c "SELECT COUNT(*) FROM request_history WHERE created_at >= NOW() - INTERVAL '24 hours';" -t
echo ""

# 7. Grafana 대시보드 확인
echo "[7/7] Grafana 대시보드 확인"
echo "http://grafana-url/dashboards"
echo ""

echo "=== 체크 완료 ==="
```

### 주간 체크리스트

- [ ] Grafana 대시보드 전체 검토
- [ ] 캐시 히트율 분석 (목표: 60% 이상)
- [ ] 느린 쿼리 확인 및 최적화
- [ ] 디스크 사용량 확인
- [ ] 백업 파일 검증
- [ ] 알림 규칙 검토

### 월간 체크리스트

- [ ] 성능 트렌드 분석
- [ ] 비용 분석 (LLM, 인프라)
- [ ] 보안 패치 적용
- [ ] 로그 아카이빙
- [ ] 장애 복구 테스트
- [ ] 문서 업데이트

---

## 모니터링

### Grafana 대시보드 접근

```bash
# Port-forward로 접근
kubectl port-forward -n agent-system svc/grafana 3000:3000

# 브라우저에서 http://localhost:3000
# 로그인: admin / <설정한 비밀번호>
```

### 주요 대시보드

| 대시보드 | 용도 | 주요 메트릭 |
|---------|------|-----------|
| **시스템 리소스** | Pod 리소스 모니터링 | CPU, 메모리, 네트워크 I/O |
| **API 성능** | 응답 시간 및 처리량 | Latency (P50/P95/P99), RPS, 에러율 |
| **비즈니스 메트릭** | 이슈 처리 현황 | 처리 건수, Agent별 분포, 성공률 |
| **캐시 효율성** | 캐싱 성능 | 히트율, 미스율, 절감 비용 |
| **이력 분석** | DB 데이터 분석 | 일별 트렌드, 파일 변경 이력 |
| **비용 분석** | 운영 비용 | LLM 토큰, API 호출 |
| **에러 추적** | 장애 모니터링 | 에러 유형, 발생 빈도 |

### 핵심 메트릭 정상 범위

| 메트릭 | 정상 범위 | 경고 | 위험 |
|-------|----------|------|------|
| CPU 사용률 | < 60% | 60-80% | > 80% |
| 메모리 사용률 | < 70% | 70-85% | > 85% |
| 평균 응답 시간 | < 3초 | 3-5초 | > 5초 |
| 에러율 | < 1% | 1-5% | > 5% |
| 캐시 히트율 | > 60% | 40-60% | < 40% |
| DB 연결 수 | < 50 | 50-80 | > 80 |

---

## 알림 대응

### 알림 종류 및 대응

#### 1. RouterHighErrorRate

**알림 내용**: Router Agent 에러율 급증 (> 10%)

**원인**:
- LLM API 장애
- 잘못된 Webhook 페이로드
- Agent 연결 실패

**대응**:
```bash
# 1. 에러 로그 확인
kubectl logs -n agent-system -l app=router-agent --tail=100 | grep ERROR

# 2. LLM API 상태 확인
curl https://api.openai.com/v1/models

# 3. Agent 헬스 체크
curl http://router-agent/agents

# 4. 필요시 Pod 재시작
kubectl rollout restart deployment router-agent -n agent-system
```

#### 2. SDBHighLatency

**알림 내용**: SDB Agent 처리 시간 급증 (P95 > 10초)

**원인**:
- Bitbucket API 지연
- LLM 응답 지연
- 대용량 파일 처리

**대응**:
```bash
# 1. 느린 요청 확인
kubectl logs -n agent-system -l app=sdb-agent | grep "처리 완료" | tail -20

# 2. Bitbucket API 상태 확인
curl https://bitbucket.org/status

# 3. 캐시 히트율 확인
kubectl exec -n agent-system deploy/redis -- redis-cli INFO stats

# 4. HPA 스케일 업 확인
kubectl get hpa -n agent-system
```

#### 3. PodRestarting

**알림 내용**: Pod 재시작 발생

**원인**:
- OOM (Out of Memory)
- Liveness probe 실패
- 애플리케이션 크래시

**대응**:
```bash
# 1. Pod 이벤트 확인
kubectl describe pod <pod-name> -n agent-system

# 2. 재시작 이유 확인
kubectl get pod <pod-name> -n agent-system -o jsonpath='{.status.containerStatuses[0].lastState}'

# 3. 이전 로그 확인 (크래시 전)
kubectl logs <pod-name> -n agent-system --previous

# 4. 리소스 증가 필요시 values.yaml 수정
```

#### 4. HighMemoryUsage

**알림 내용**: 메모리 사용률 > 90%

**대응**:
```bash
# 1. 메모리 프로파일링
kubectl top pod -n agent-system

# 2. 캐시 크기 확인
kubectl exec -n agent-system deploy/redis -- redis-cli INFO memory

# 3. DB 연결 풀 확인
kubectl logs -n agent-system -l app=router-agent | grep "connection pool"

# 4. 긴급 조치: Pod 재시작
kubectl delete pod <pod-name> -n agent-system
```

---

## 트러블슈팅

### 일반적인 문제 해결

#### 문제 1: Webhook 요청이 처리되지 않음

**증상**: Jira에서 Webhook 전송했으나 응답 없음

**진단**:
```bash
# Ingress 상태 확인
kubectl get ingress -n agent-system
kubectl describe ingress agent-ingress -n agent-system

# Router Agent Pod 상태
kubectl get pods -n agent-system -l app=router-agent

# 로그 확인
kubectl logs -n agent-system -l app=router-agent --tail=50
```

**해결**:
1. Ingress가 Router Service를 올바르게 가리키는지 확인
2. Router Pod가 Running 상태인지 확인
3. Network Policy가 트래픽을 차단하지 않는지 확인

#### 문제 2: 캐시가 동작하지 않음

**증상**: 모든 요청이 캐시 MISS

**진단**:
```bash
# Redis 연결 확인
kubectl exec -n agent-system deploy/redis -- redis-cli PING

# Redis 키 확인
kubectl exec -n agent-system deploy/redis -- redis-cli KEYS "*"

# Agent 로그에서 캐시 관련 메시지 확인
kubectl logs -n agent-system -l app=router-agent | grep "캐시"
```

**해결**:
1. Redis Service DNS 확인: `nslookup redis.agent-system.svc.cluster.local`
2. Agent 환경 변수 확인: `REDIS_HOST`, `REDIS_PORT`
3. Redis ConfigMap 확인
4. 필요시 Agent 재시작

#### 문제 3: DB 연결 실패

**증상**: "DB 연결 실패" 로그 메시지

**진단**:
```bash
# PostgreSQL Pod 상태
kubectl get pods -n agent-system -l app=postgresql

# PostgreSQL 서비스 확인
kubectl get svc postgresql -n agent-system

# 직접 연결 테스트
kubectl exec -n agent-system postgresql-0 -- psql -U agent_user -d agent_system -c "SELECT 1;"
```

**해결**:
1. PostgreSQL Pod가 Ready 상태인지 확인
2. Secret의 비밀번호가 올바른지 확인
3. Agent 환경 변수 확인: `DB_HOST`, `DB_PASSWORD`
4. 네트워크 Policy 확인

#### 문제 4: Prometheus가 메트릭을 수집하지 못함

**증상**: Grafana 대시보드에 데이터 없음

**진단**:
```bash
# Prometheus Targets 확인
kubectl port-forward -n agent-system svc/prometheus 9090:9090
# http://localhost:9090/targets

# Agent 메트릭 엔드포인트 직접 확인
kubectl exec -n agent-system <router-pod> -- curl localhost:5000/metrics
```

**해결**:
1. Pod annotations 확인 (`prometheus.io/scrape: "true"`)
2. Service가 올바른 Pod를 선택하는지 확인
3. Prometheus RBAC 권한 확인
4. Prometheus ConfigMap 확인

---

## 백업 및 복구

### PostgreSQL 백업

#### 자동 백업 (CronJob)

```bash
# 백업 CronJob 확인
kubectl get cronjob -n agent-system

# 수동 백업 실행
kubectl create job --from=cronjob/postgresql-backup manual-backup-$(date +%Y%m%d) -n agent-system

# 백업 파일 확인
kubectl exec -n agent-system postgresql-0 -- ls -lh /backup
```

#### 수동 백업

```bash
# 즉시 백업
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
kubectl exec -n agent-system postgresql-0 -- \
  pg_dump -U agent_user -d agent_system | \
  gzip > backup_${TIMESTAMP}.sql.gz

echo "Backup saved: backup_${TIMESTAMP}.sql.gz"
```

### PostgreSQL 복구

```bash
# 1. 백업 파일 Pod로 복사
kubectl cp backup_20251022_020000.sql.gz \
  agent-system/postgresql-0:/tmp/backup.sql.gz

# 2. 복구 실행
kubectl exec -n agent-system postgresql-0 -- bash -c \
  "gunzip < /tmp/backup.sql.gz | psql -U agent_user -d agent_system"

# 3. 검증
kubectl exec -n agent-system postgresql-0 -- \
  psql -U agent_user -d agent_system -c "SELECT COUNT(*) FROM request_history;"
```

### Redis 백업 (옵션)

Redis는 캐시 용도이므로 백업이 필수는 아니지만, 필요시:

```bash
# RDB 스냅샷 생성
kubectl exec -n agent-system deploy/redis -- redis-cli BGSAVE

# 스냅샷 파일 복사
kubectl cp agent-system/<redis-pod>:/data/dump.rdb ./dump.rdb
```

---

## 스케일링

### 수동 스케일링

```bash
# Router Agent 스케일 업
kubectl scale deployment router-agent --replicas=5 -n agent-system

# SDB Agent 스케일 업
kubectl scale deployment sdb-agent --replicas=4 -n agent-system

# 확인
kubectl get pods -n agent-system
```

### HPA 설정 조정

```bash
# HPA 편집
kubectl edit hpa router-agent-hpa -n agent-system

# 변경 예시:
# minReplicas: 3 → 5
# maxReplicas: 10 → 20
# targetCPUUtilizationPercentage: 70 → 60

# 적용 확인
kubectl get hpa -n agent-system
```

### 리소스 요청/제한 조정

**파일**: `helm/multi-agent-system/values.yaml` (수정 후 upgrade)

```yaml
routerAgent:
  resources:
    requests:
      cpu: 500m  # 증가
      memory: 1Gi  # 증가
    limits:
      cpu: 2000m  # 증가
      memory: 2Gi  # 증가
```

```bash
# 적용
helm upgrade multi-agent-system ./helm/multi-agent-system \
  -f ./helm/multi-agent-system/values.yaml \
  -n agent-system
```

---

## 업데이트 및 배포

### 이미지 업데이트

```bash
# 1. 새 이미지 빌드 및 푸시
docker build -t your-registry/router-agent:v1.1.0 ./router-agent
docker push your-registry/router-agent:v1.1.0

# 2. Deployment 이미지 업데이트
kubectl set image deployment/router-agent \
  router-agent=your-registry/router-agent:v1.1.0 \
  -n agent-system

# 3. 롤아웃 상태 확인
kubectl rollout status deployment/router-agent -n agent-system

# 4. 롤백 (필요시)
kubectl rollout undo deployment/router-agent -n agent-system
```

### Helm Chart 업데이트

```bash
# 1. values.yaml 수정

# 2. Dry-run으로 변경사항 확인
helm upgrade multi-agent-system ./helm/multi-agent-system \
  -f values.yaml \
  -n agent-system \
  --dry-run --debug

# 3. 실제 업그레이드
helm upgrade multi-agent-system ./helm/multi-agent-system \
  -f values.yaml \
  -n agent-system

# 4. 롤백 (필요시)
helm rollback multi-agent-system -n agent-system
```

### ConfigMap/Secret 업데이트

```bash
# ConfigMap 수정
kubectl edit configmap postgresql-config -n agent-system

# Pod 재시작 (ConfigMap 반영)
kubectl rollout restart deployment router-agent -n agent-system

# Secret 업데이트
kubectl create secret generic agent-secrets \
  --from-literal=openai-api-key='new-key' \
  --dry-run=client -o yaml | kubectl apply -f -
```

---

## 보안

### 비밀번호 관리

```bash
# PostgreSQL 비밀번호 변경
NEW_PASSWORD="new-strong-password"

# 1. PostgreSQL에서 변경
kubectl exec -n agent-system postgresql-0 -- \
  psql -U agent_user -d agent_system -c "ALTER USER agent_user WITH PASSWORD '$NEW_PASSWORD';"

# 2. Secret 업데이트
kubectl create secret generic postgresql-secret \
  --from-literal=POSTGRES_PASSWORD="$NEW_PASSWORD" \
  --dry-run=client -o yaml -n agent-system | kubectl apply -f -

# 3. Agent Pod 재시작
kubectl rollout restart deployment router-agent -n agent-system
kubectl rollout restart deployment sdb-agent -n agent-system
```

### 네트워크 Policy

```yaml
# network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: agent-network-policy
  namespace: agent-system
spec:
  podSelector:
    matchLabels:
      tier: worker  # SDB Agent 등
  policyTypes:
    - Ingress
  ingress:
    # Router Agent에서만 접근 허용
    - from:
        - podSelector:
            matchLabels:
              tier: orchestrator
      ports:
        - protocol: TCP
          port: 5000
```

### 로그 마스킹

```python
# 민감 정보 로깅 방지
import re

def mask_sensitive_data(log_message: str) -> str:
    """민감 정보 마스킹"""
    # API 키 마스킹
    log_message = re.sub(r'(api[_-]?key["\s:=]+)[\w-]+', r'\1***', log_message, flags=re.I)
    # 토큰 마스킹
    log_message = re.sub(r'(token["\s:=]+)[\w-]+', r'\1***', log_message, flags=re.I)
    # 비밀번호 마스킹
    log_message = re.sub(r'(password["\s:=]+)[\w-]+', r'\1***', log_message, flags=re.I)
    return log_message

logger.info(mask_sensitive_data(message))
```

---

## 유용한 명령어 모음

### 빠른 진단

```bash
# 전체 시스템 상태 한눈에
kubectl get all -n agent-system

# 최근 이벤트
kubectl get events -n agent-system --sort-by='.lastTimestamp' | tail -20

# 리소스 사용량
kubectl top pods -n agent-system
kubectl top nodes

# 로그 스트리밍 (여러 Pod)
stern -n agent-system router-agent

# Pod 셸 접속
kubectl exec -it <pod-name> -n agent-system -- /bin/bash
```

### 디버깅

```bash
# Pod 상세 정보
kubectl describe pod <pod-name> -n agent-system

# 네트워크 연결 테스트
kubectl run tmp-shell --rm -i --tty --image nicolaka/netshoot -n agent-system

# DNS 조회
kubectl run tmp-shell --rm -i --tty --image busybox -n agent-system -- \
  nslookup redis.agent-system.svc.cluster.local

# Port-forward
kubectl port-forward <pod-name> 8080:5000 -n agent-system
```

---

## 긴급 상황 대응

### 시스템 전체 장애

```bash
# 1. 모든 Pod 상태 확인
kubectl get pods -n agent-system

# 2. 최근 변경사항 확인
helm history multi-agent-system -n agent-system

# 3. 롤백
helm rollback multi-agent-system <revision> -n agent-system

# 4. Pod 강제 재시작
kubectl delete pod --all -n agent-system
```

### DB 데이터 손상

```bash
# 1. 백업에서 복구 (위 백업 섹션 참조)

# 2. 데이터 정합성 확인
kubectl exec -n agent-system postgresql-0 -- \
  psql -U agent_user -d agent_system -c "SELECT COUNT(*) FROM request_history;"

# 3. 인덱스 재생성
kubectl exec -n agent-system postgresql-0 -- \
  psql -U agent_user -d agent_system -c "REINDEX DATABASE agent_system;"
```

### 캐시 오염

```bash
# 모든 캐시 삭제
kubectl exec -n agent-system deploy/redis -- redis-cli FLUSHALL

# 또는 특정 패턴만 삭제
kubectl exec -n agent-system deploy/redis -- redis-cli --scan --pattern "classification:*" | \
  xargs kubectl exec -n agent-system deploy/redis -- redis-cli DEL
```

---

## 참고 자료

### 내부 문서
- [OVERVIEW.md](./OVERVIEW.md) - 전체 아키텍처
- [PHASE1_MONITORING.md](./PHASE1_MONITORING.md) - 모니터링 구축
- [PHASE2_REDIS.md](./PHASE2_REDIS.md) - Redis 캐싱
- [PHASE3_POSTGRESQL.md](./PHASE3_POSTGRESQL.md) - PostgreSQL 이력
- [DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md) - DB 스키마

### 외부 자료
- [Kubernetes 공식 문서](https://kubernetes.io/docs/)
- [Helm 공식 문서](https://helm.sh/docs/)
- [Prometheus 공식 문서](https://prometheus.io/docs/)
- [Grafana 공식 문서](https://grafana.com/docs/)

---

**문서 버전**: 1.0.0
**최종 업데이트**: 2025-10-22
**담당자**: DevOps Team
