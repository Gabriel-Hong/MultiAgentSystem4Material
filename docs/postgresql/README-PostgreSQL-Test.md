# PostgreSQL 통합 테스트 가이드

PostgreSQL 데이터베이스 연동을 검증하기 위한 테스트 스크립트입니다.

---

## 📋 테스트 스크립트 목록

### 1. `test-postgresql.sh` (완전 버전)
Router Agent로 가짜 Webhook을 전송하고 PostgreSQL DB에 데이터가 올바르게 저장되는지 **자동으로 검증**하는 스크립트입니다.

**특징:**
- ✅ Kubernetes 리소스 자동 확인 (PostgreSQL, Router Agent)
- ✅ 테이블 존재 여부 확인
- ✅ 가짜 Webhook 자동 전송
- ✅ DB 저장 여부 자동 검증 (Pass/Fail)
- ✅ 상세 데이터 조회 및 출력
- ✅ 색상 출력으로 가독성 향상

### 2. `test-postgresql-simple.sh` (간단 버전)
빠르게 Webhook을 전송하고 DB에 저장된 데이터를 조회하는 **간소화된 버전**입니다.

**특징:**
- ✅ 빠른 실행 (검증 로직 최소화)
- ✅ 최근 데이터 조회에 집중
- ✅ 간단한 출력 형식

---

## 🚀 사용 방법

### 사전 준비

1. **Kubernetes 클러스터 접근 가능**
   ```bash
   kubectl get nodes
   ```

2. **agent-system 네임스페이스에 PostgreSQL 및 Router Agent 배포됨**
   ```bash
   kubectl get pod -n agent-system
   ```

3. **curl, jq 설치 (선택사항)**
   ```bash
   # Windows (Git Bash 또는 WSL)
   # curl은 대부분 기본 설치됨

   # jq 설치 (선택사항 - 없어도 실행 가능)
   # https://stedolan.github.io/jq/download/
   ```

---

## 📝 테스트 시나리오

### 시나리오 1: 완전 자동 검증 테스트

```bash
# scripts 디렉토리로 이동
cd scripts

# 완전 버전 실행
./test-postgresql.sh
```

**실행 단계:**
1. ✅ Kubernetes 리소스 확인 (PostgreSQL, Router Agent, Services)
2. ✅ PostgreSQL 연결 테스트
3. ✅ 테스트 전 데이터 상태 확인
4. ✅ 가짜 Webhook 전송 (TEST-DB-001)
5. ✅ 데이터베이스 검증
   - `request_history` 저장 확인
   - `classification_history` 저장 확인
   - `performance_metrics` 저장 확인
6. ✅ 저장된 데이터 상세 조회
7. ✅ 결과 요약 (Pass/Fail)

**예상 출력:**
```
========================================
PostgreSQL 통합 테스트
========================================

[1/6] Kubernetes 리소스 확인 중...

  - PostgreSQL Pod: ✓ Running
  - Router Agent Pod: ✓ Running
  - PostgreSQL Service: ✓ Exists
  - Router Agent Service: ✓ Exists

[2/6] PostgreSQL 연결 테스트...

  PostgreSQL Pod: postgresql-0
  - 테이블 존재 확인: ✓ 4개 테이블 확인

[3/6] 테스트 전 데이터 상태 확인...

  - 기존 request_history (TEST-DB-001): 0
  - 기존 classification_history (TEST-DB-001): 0

[4/6] 가짜 Webhook 전송 중...

  Port-forward 시작: localhost:8080 -> router-agent-svc:5000
  Webhook 페이로드:
    {
      "webhookEvent": "jira:issue_created",
      "issue": {
        "key": "TEST-DB-001",
        ...
      }
    }

  Webhook 전송: ✓ 성공 (HTTP 200)

[5/6] 데이터베이스 검증 중...

  데이터 저장 대기 중 (3초)...
  - request_history 저장 확인: ✓ 저장됨 (+1건)
  - classification_history 저장 확인: ✓ 저장됨 (+1건)
  - performance_metrics 저장 확인: ✓ 저장됨 (1건)

[6/6] 저장된 데이터 상세 조회...

  📝 최근 저장된 request_history:
   id | issue_key  | webhook_event      | status     | created_at
  ----+------------+-------------------+------------+-------------------------
    1 | TEST-DB-001| jira:issue_created | processing | 2025-11-04 10:30:15.123

  🎯 최근 저장된 classification_history:
   id | issue_key  | classified_agent | confidence | cached | created_at
  ----+------------+------------------+------------+--------+-------------------------
    1 | TEST-DB-001| sdb-agent        | 0.95       | f      | 2025-11-04 10:30:15.456

  📊 최근 저장된 performance_metrics (router-agent):
   id | agent_name   | metric_type | metric_value | created_at
  ----+--------------+-------------+--------------+-------------------------
    1 | router-agent | latency     | 2.34         | 2025-11-04 10:30:16.789

========================================
테스트 결과 요약
========================================

  ✓ request_history 저장
  ✓ classification_history 저장
  ✓ performance_metrics 저장

  통과: 3/3

========================================
✓ PostgreSQL 통합 테스트 성공!
========================================
```

---

### 시나리오 2: 간단 버전 테스트

```bash
# 간단 버전 실행
./test-postgresql-simple.sh
```

**실행 단계:**
1. ✅ Port-forward 시작
2. ✅ Webhook 전송
3. ✅ DB 저장 대기
4. ✅ 최근 데이터 조회

**예상 출력:**
```
PostgreSQL 통합 테스트 (간단 버전)
======================================

1. Router Agent Port-forward 시작...
2. 테스트 Webhook 전송...
✓ Webhook 전송 완료
3. DB 저장 대기 중...
4. PostgreSQL 데이터 조회...

📝 최근 request_history (상위 3건):
 id | issue_key     | status     | created_at
----+---------------+------------+-------------------------
  3 | TEST-DB-10305 | processing | 2025-11-04 10:30:45.123
  2 | TEST-DB-001   | completed  | 2025-11-04 10:30:15.123
  1 | TEST-DB-001   | processing | 2025-11-04 10:25:10.456

🎯 최근 classification_history (상위 3건):
 id | issue_key     | classified_agent | confidence | cached
----+---------------+------------------+------------+--------
  3 | TEST-DB-10305 | sdb-agent        | 0.95       | f
  2 | TEST-DB-001   | sdb-agent        | 0.92       | t
  1 | TEST-DB-001   | sdb-agent        | 0.95       | f

📊 최근 performance_metrics (상위 5건):
 id | agent_name   | metric_type | value
----+--------------+-------------+-------
  5 | router-agent | latency     | 1.23
  4 | sdb-agent    | latency     | 5.67
  3 | router-agent | latency     | 2.34
  2 | router-agent | latency     | 1.89
  1 | router-agent | latency     | 2.45

======================================
테스트 완료!
======================================
```

---

## 🔍 수동 검증 방법

### 1. PostgreSQL 직접 접속

```bash
# PostgreSQL Pod 이름 확인
kubectl get pod -n agent-system -l app=postgresql

# PostgreSQL 접속
kubectl exec -it postgresql-0 -n agent-system -- psql -U agent_user -d agent_system
```

### 2. 테이블 조회

```sql
-- 테이블 목록
\dt

-- request_history 조회
SELECT * FROM request_history ORDER BY created_at DESC LIMIT 5;

-- classification_history 조회
SELECT * FROM classification_history ORDER BY created_at DESC LIMIT 5;

-- code_change_history 조회
SELECT * FROM code_change_history ORDER BY created_at DESC LIMIT 5;

-- performance_metrics 조회
SELECT * FROM performance_metrics ORDER BY created_at DESC LIMIT 10;

-- 이슈 키로 전체 이력 조회
SELECT
    rh.id,
    rh.issue_key,
    rh.status,
    ch.classified_agent,
    ch.confidence,
    COUNT(cch.id) AS files_changed
FROM request_history rh
LEFT JOIN classification_history ch ON rh.id = ch.request_id
LEFT JOIN code_change_history cch ON rh.id = cch.request_id
WHERE rh.issue_key = 'TEST-DB-001'
GROUP BY rh.id, ch.id
ORDER BY rh.created_at DESC;
```

### 3. 통계 조회

```sql
-- 전체 요청 수
SELECT COUNT(*) FROM request_history;

-- Agent별 처리 건수
SELECT classified_agent, COUNT(*)
FROM classification_history
GROUP BY classified_agent;

-- 평균 처리 시간
SELECT agent_name,
       AVG(metric_value) as avg_latency,
       MAX(metric_value) as max_latency
FROM performance_metrics
WHERE metric_type = 'latency'
GROUP BY agent_name;

-- 캐시 히트율
SELECT
    COUNT(*) FILTER (WHERE cached = true) * 100.0 / COUNT(*) as cache_hit_rate
FROM classification_history;
```

---

## 🐛 트러블슈팅

### 문제 1: "PostgreSQL Pod가 실행 중이 아닙니다"

**원인:** PostgreSQL이 아직 배포되지 않았거나 시작 중입니다.

**해결:**
```bash
# PostgreSQL Pod 상태 확인
kubectl get pod -n agent-system -l app=postgresql

# PostgreSQL 로그 확인
kubectl logs -f postgresql-0 -n agent-system

# Helm 재배포 (필요시)
helm upgrade multi-agent-system ./helm/multi-agent-system -n agent-system
```

---

### 문제 2: "테이블이 존재하지 않습니다"

**원인:** 초기화 스크립트가 실행되지 않았습니다.

**해결:**
```bash
# PostgreSQL Pod 재시작
kubectl delete pod postgresql-0 -n agent-system

# 초기화 스크립트 확인
kubectl get configmap postgresql-init-scripts -n agent-system -o yaml

# 수동으로 스키마 생성
kubectl exec -it postgresql-0 -n agent-system -- psql -U agent_user -d agent_system

# 그 후 DATABASE_SCHEMA.md의 SQL 실행
```

---

### 문제 3: "데이터가 저장되지 않음"

**원인:** Router Agent가 DB에 연결하지 못했습니다.

**해결:**
```bash
# Router Agent 로그 확인
kubectl logs -f deployment/router-agent -n agent-system | grep -i "db\|postgres\|database"

# 예상 로그:
# "DB 연결 풀 생성 성공: postgresql:5432/agent_system"
# "요청 이력 생성: TEST-DB-001 (ID: 1)"

# 환경 변수 확인
kubectl exec deployment/router-agent -n agent-system -- env | grep DB

# DB 연결 테스트 (Router Agent Pod에서)
kubectl exec -it deployment/router-agent -n agent-system -- nc -zv postgresql 5432
```

---

### 문제 4: "Webhook 전송 실패 (HTTP 000)"

**원인:** Port-forward가 제대로 설정되지 않았습니다.

**해결:**
```bash
# 기존 Port-forward 종료
pkill -f "port-forward.*router-agent" || true

# 수동 Port-forward 시작
kubectl port-forward -n agent-system svc/router-agent-svc 8080:5000

# 다른 터미널에서 Health Check
curl http://localhost:8080/health

# 정상 응답:
# {"status":"healthy","timestamp":"2025-11-04T10:30:00","agents":{...}}
```

---

## 📊 예상 결과

### 성공 시나리오

| 테스트 항목 | 예상 결과 | 설명 |
|------------|----------|------|
| PostgreSQL Pod | ✅ Running | StatefulSet으로 배포됨 |
| Router Agent Pod | ✅ Running | 환경 변수로 DB 연결 정보 주입 |
| 테이블 생성 | ✅ 4개 테이블 | init-scripts로 자동 생성 |
| Webhook 전송 | ✅ HTTP 200 | Router Agent 정상 응답 |
| request_history | ✅ 저장됨 | issue_key, payload, status 저장 |
| classification_history | ✅ 저장됨 | agent, confidence, reasoning 저장 |
| performance_metrics | ✅ 저장됨 | latency 메트릭 저장 |

### 실패 시나리오

| 증상 | 원인 | 해결 방법 |
|-----|------|----------|
| DB 연결 실패 | Secret 미생성 | `kubectl get secret postgresql-secret -n agent-system` 확인 |
| 테이블 없음 | 초기화 실패 | PostgreSQL Pod 재시작 |
| 데이터 미저장 | Agent 환경 변수 누락 | Deployment 환경 변수 확인 |
| Webhook 실패 | Port-forward 문제 | Port-forward 재시작 |

---

## 📚 추가 자료

- **DATABASE_SCHEMA.md**: 테이블 스키마 상세 정보
- **PHASE3_POSTGRESQL.md**: PostgreSQL 적용 가이드
- **scripts/test-redis-caching.sh**: Redis 캐싱 테스트 (참고용)

---

## ✅ 체크리스트

배포 후 다음 항목들을 확인하세요:

- [ ] PostgreSQL Pod가 Running 상태
- [ ] 4개 테이블이 모두 생성됨
- [ ] Router Agent가 DB에 연결됨 (로그 확인)
- [ ] SDB Agent가 DB에 연결됨 (로그 확인)
- [ ] `test-postgresql.sh` 실행 시 모든 테스트 통과
- [ ] Webhook 전송 시 DB에 데이터 저장
- [ ] Classification 결과가 DB에 저장
- [ ] Performance 메트릭이 DB에 저장

---

**문서 버전**: 1.0.0
**최종 업데이트**: 2025-11-04
