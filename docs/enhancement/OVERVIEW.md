# 멀티 에이전트 시스템 고도화 계획

## 문서 정보
- **버전**: 1.0.0
- **작성일**: 2025-10-22
- **대상 시스템**: Multi-Agent Development System (MoE 기반)

---

## 목차
1. [개요](#개요)
2. [현재 시스템 구조](#현재-시스템-구조)
3. [고도화 목표](#고도화-목표)
4. [전체 아키텍처](#전체-아키텍처)
5. [기술 스택](#기술-스택)
6. [구현 단계](#구현-단계)
7. [예상 효과](#예상-효과)
8. [다음 단계](#다음-단계)

---

## 개요

본 문서는 현재 구축된 Kubernetes 기반 Multi-Agent 시스템을 고도화하는 전체 계획을 담고 있습니다. 주요 고도화 내용은 다음과 같습니다:

- **모니터링**: Prometheus + Grafana를 통한 종합 모니터링
- **캐싱**: Redis를 활용한 Bitbucket API 및 LLM 응답 캐싱
- **이력 관리**: PostgreSQL을 통한 요청/응답/코드 변경 이력 저장
- **통합 최적화**: 전체 시스템 성능 및 운영 효율성 개선

---

## 현재 시스템 구조

### 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                        │
│                                                               │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Ingress Controller (NGINX)                        │    │
│  └──────────────────────┬─────────────────────────────┘    │
│                         ↓                                    │
│  ┌────────────────────────────────────────────────────┐    │
│  │         Router Agent (FastAPI)                     │    │
│  │  - Intent Classification (LLM)                     │    │
│  │  - Agent Registry                                  │    │
│  │  - Load Balancing                                  │    │
│  │  Replicas: 3 (HPA)                                 │    │
│  └───────┬────────────────────────────────────────────┘    │
│          │                                                   │
│          ↓                                                   │
│  ┌────────────────────────────────────────────────────┐    │
│  │         SDB Agent (Flask)                          │    │
│  │  - Bitbucket API Integration                       │    │
│  │  - LLM-based Code Generation                       │    │
│  │  - PR Creation                                     │    │
│  │  Replicas: 2 (HPA)                                 │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### 현재 구성 요소

| 컴포넌트 | 기술 | 역할 | 배포 형태 |
|---------|------|------|----------|
| Router Agent | FastAPI | Webhook 수신 및 라우팅 | Deployment (3 Pods) |
| SDB Agent | Flask | 코드 생성 및 PR 생성 | Deployment (2 Pods) |
| Ingress | NGINX | 외부 트래픽 진입점 | Ingress Controller |

### 현재 기능

✅ **구현 완료**:
- Jira Webhook 수신
- LLM 기반 Intent Classification
- Agent 라우팅 및 호출
- Bitbucket API 연동
- 코드 자동 생성 및 PR 생성
- Kubernetes HPA (자동 스케일링)

❌ **미구현**:
- 종합 모니터링 시스템
- API 응답 캐싱
- 요청/응답 이력 관리
- 성능 메트릭 수집
- 비용 추적

---

## 고도화 목표

### 1. 가시성 확보 (Observability)
- **목표**: 시스템 전체 상태를 실시간으로 파악
- **방법**: Prometheus + Grafana를 통한 메트릭 수집 및 시각화
- **측정 지표**:
  - Pod CPU/메모리 사용률
  - API 응답 시간 (P50, P95, P99)
  - 요청 처리량 (RPS)
  - 에러율 및 성공률

### 2. 성능 최적화
- **목표**: 응답 시간 50% 단축, API 호출 70% 감소
- **방법**: Redis 캐싱 적용
- **캐싱 대상**:
  - Bitbucket API 응답 (저장소 정보, 브랜치 목록)
  - LLM Intent Classification 결과
  - LLM 코드 생성 결과 (유사 요청)

### 3. 이력 관리 및 분석
- **목표**: 모든 요청/응답 이력을 저장하여 분석 가능
- **방법**: PostgreSQL 데이터베이스 도입
- **저장 데이터**:
  - 요청/응답 전체 내역
  - Intent Classification 결과
  - 코드 변경 내역 및 Diff
  - 성능 메트릭 (처리 시간, LLM 토큰 사용량)

### 4. 운영 효율성 향상
- **목표**: 장애 감지 시간 80% 단축, 디버깅 시간 50% 감소
- **방법**: 통합 모니터링 및 알림 시스템
- **기능**:
  - 자동 알림 (에러율 급증, 응답 시간 초과)
  - 대시보드를 통한 실시간 모니터링
  - 이력 기반 문제 원인 분석

---

## 전체 아키텍처

### 고도화 후 아키텍처

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Kubernetes Cluster                            │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  Ingress Controller                                         │    │
│  └────────────────────────┬───────────────────────────────────┘    │
│                           ↓                                          │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  Router Agent (FastAPI)                                     │    │
│  │  ┌───────────────────────────────────────────────────┐     │    │
│  │  │ 1. Webhook 수신                                    │     │    │
│  │  │ 2. DB: Request History 저장                       │     │    │
│  │  │ 3. Redis: Classification 캐시 체크                │     │    │
│  │  │ 4. LLM: Intent Classification (캐시 미스시)       │     │    │
│  │  │ 5. DB: Classification History 저장                │     │    │
│  │  │ 6. Prometheus: 메트릭 기록                        │     │    │
│  │  └───────────────────────────────────────────────────┘     │    │
│  │  Replicas: 3 (HPA)                                          │    │
│  └───────┬────────────────────────────────────────────────────┘    │
│          │                                                           │
│          ↓                                                           │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  SDB Agent (Flask)                                          │    │
│  │  ┌───────────────────────────────────────────────────┐     │    │
│  │  │ 1. Redis: Bitbucket API 캐시 체크                 │     │    │
│  │  │ 2. Redis: LLM 응답 캐시 체크                      │     │    │
│  │  │ 3. Bitbucket: API 호출 (캐시 미스시)              │     │    │
│  │  │ 4. LLM: 코드 생성 (캐시 미스시)                   │     │    │
│  │  │ 5. DB: Code Change History 저장                   │     │    │
│  │  │ 6. DB: Performance Metrics 저장                   │     │    │
│  │  │ 7. Prometheus: 메트릭 기록                        │     │    │
│  │  └───────────────────────────────────────────────────┘     │    │
│  │  Replicas: 2 (HPA)                                          │    │
│  └─────┬───────────┬──────────────┬─────────────────────────────┘    │
│        │           │              │                                   │
│        ↓           ↓              ↓                                   │
│  ┌──────────┐ ┌─────────────┐ ┌──────────────┐                     │
│  │  Redis   │ │ PostgreSQL  │ │  Prometheus  │                     │
│  │          │ │             │ │              │                     │
│  │ - Cache  │ │ - Request   │ │ + Grafana    │                     │
│  │ - Queue  │ │ - History   │ │              │                     │
│  │          │ │ - Metrics   │ │ - Metrics    │                     │
│  │          │ │             │ │ - Dashboards │                     │
│  │ Pod x 1  │ │ StatefulSet │ │ - Alerts     │                     │
│  └──────────┘ └─────────────┘ └──────────────┘                     │
└───────────────────────────────────────────────────────────────────┘
```

### 데이터 흐름

```
Jira Webhook
    ↓
[Router Agent]
    ├─→ PostgreSQL: request_history INSERT
    ├─→ Redis: GET classification:{hash}
    ├─→ OpenAI: classify_issue() [캐시 미스시]
    ├─→ Redis: SET classification:{hash}
    ├─→ PostgreSQL: classification_history INSERT
    ├─→ Prometheus: router_requests_total++
    ↓
[SDB Agent]
    ├─→ Redis: GET bitbucket:repo:{workspace}:{repo}
    ├─→ Bitbucket API: get_repository() [캐시 미스시]
    ├─→ Redis: SET bitbucket:repo:{workspace}:{repo}
    ├─→ Redis: GET llm:code:{hash}
    ├─→ OpenAI: generate_code() [캐시 미스시]
    ├─→ Redis: SET llm:code:{hash}
    ├─→ PostgreSQL: code_change_history INSERT
    ├─→ PostgreSQL: performance_metrics INSERT
    ├─→ Prometheus: sdb_processing_duration_seconds.observe()
    ↓
Bitbucket PR Created
```

---

## 기술 스택

### 신규 도입 기술

| 카테고리 | 기술 | 버전 | 용도 |
|---------|------|------|------|
| **모니터링** | Prometheus | 2.45+ | 메트릭 수집 |
| | Grafana | 10.0+ | 메트릭 시각화 |
| **캐싱** | Redis | 7.0+ | API/LLM 응답 캐싱 |
| **데이터베이스** | PostgreSQL | 15+ | 이력 및 메트릭 저장 |
| **Python 라이브러리** | prometheus_client | 0.18+ | FastAPI 메트릭 |
| | prometheus_flask_exporter | 0.22+ | Flask 메트릭 |
| | redis-py | 5.0+ | Redis 클라이언트 |
| | psycopg2-binary | 2.9+ | PostgreSQL 클라이언트 |
| | SQLAlchemy | 2.0+ | ORM (옵션) |

### 기존 기술 스택 (유지)

| 카테고리 | 기술 | 용도 |
|---------|------|------|
| **Orchestration** | Kubernetes | 컨테이너 오케스트레이션 |
| | Helm | 패키지 관리 |
| **Backend** | FastAPI | Router Agent |
| | Flask | SDB Agent |
| **External APIs** | OpenAI API | LLM 서비스 |
| | Bitbucket API | 소스 코드 관리 |

---

## 구현 단계

### Phase 1: Prometheus + Grafana (Week 1-2)

**목표**: 시스템 가시성 확보

**작업 내용**:
1. Prometheus Helm 차트 작성
2. Grafana Helm 차트 작성
3. Router Agent 메트릭 엔드포인트 추가
4. SDB Agent 메트릭 엔드포인트 추가
5. ServiceMonitor 설정
6. Grafana 대시보드 구성 (4개)
   - 시스템 리소스 대시보드
   - API 성능 대시보드
   - 비즈니스 메트릭 대시보드
   - 에러 추적 대시보드
7. 알림 규칙 설정

**산출물**:
- `helm/multi-agent-system/templates/monitoring/prometheus/`
- `helm/multi-agent-system/templates/monitoring/grafana/`
- `router-agent/app/metrics.py`
- `sdb-agent/app/metrics.py`

**검증 기준**:
- [ ] Prometheus가 모든 Agent에서 메트릭 수집 확인
- [ ] Grafana 대시보드에서 실시간 데이터 표시 확인
- [ ] 알림 테스트 (의도적 에러 발생 → Slack/Email 알림)

**상세 가이드**: [PHASE1_MONITORING.md](./PHASE1_MONITORING.md)

---

### Phase 2: Redis 캐싱 (Week 3-4)

**목표**: API 호출 70% 감소, 응답 시간 50% 단축

**작업 내용**:
1. Redis Helm 차트 작성 및 배포
2. Router Agent Cache Manager 구현
   - Intent Classification 결과 캐싱
3. SDB Agent Cache Manager 구현
   - Bitbucket API 응답 캐싱
   - LLM 코드 생성 결과 캐싱
4. TTL 설정
   - Bitbucket API: 5분
   - LLM 응답: 24시간
5. 캐시 메트릭 추가 (히트율, 미스율)

**산출물**:
- `helm/multi-agent-system/templates/redis/`
- `router-agent/app/cache.py`
- `sdb-agent/app/cache_manager.py`

**검증 기준**:
- [ ] Redis 연결 및 동작 확인
- [ ] 캐시 히트율 50% 이상 달성
- [ ] API 호출 횟수 70% 감소 확인
- [ ] 평균 응답 시간 50% 단축 확인

**상세 가이드**: [PHASE2_REDIS.md](./PHASE2_REDIS.md)

---

### Phase 3: PostgreSQL 이력 관리 (Week 5)

**목표**: 모든 요청/응답 이력 저장 및 분석 기반 마련

**작업 내용**:
1. PostgreSQL StatefulSet 작성
2. 데이터베이스 스키마 설계
   - request_history (요청 이력)
   - classification_history (분류 이력)
   - code_change_history (코드 변경 이력)
   - performance_metrics (성능 메트릭)
3. 마이그레이션 스크립트 작성
4. Router Agent DB Manager 구현
5. SDB Agent DB Manager 구현
6. 인덱스 최적화

**산출물**:
- `helm/multi-agent-system/templates/postgresql/`
- `router-agent/app/db.py`
- `sdb-agent/app/db_manager.py`
- `docs/enhancement/DATABASE_SCHEMA.md`

**검증 기준**:
- [ ] PostgreSQL 연결 및 스키마 생성 확인
- [ ] 요청 처리 시 DB 저장 확인
- [ ] 쿼리 성능 테스트 (1000건 이상)
- [ ] 인덱스 효과 확인

**상세 가이드**: [PHASE3_POSTGRESQL.md](./PHASE3_POSTGRESQL.md)

---

### Phase 4: 통합 및 최적화 (Week 6)

**목표**: 전체 시스템 안정화 및 운영 준비

**작업 내용**:
1. 전체 시스템 통합 테스트
2. Grafana 대시보드 고도화
   - 캐시 효율성 대시보드
   - 비용 분석 대시보드
   - 이력 분석 대시보드
3. 성능 튜닝
   - 커넥션 풀 최적화
   - 인덱스 튜닝
   - 캐시 TTL 조정
4. 장애 시나리오 테스트
5. 운영 가이드 작성

**산출물**:
- 통합 테스트 스크립트
- 고도화된 Grafana 대시보드
- 운영 가이드 문서

**검증 기준**:
- [ ] 부하 테스트 통과 (100 RPS, 10분)
- [ ] 장애 복구 시간 5분 이내
- [ ] 전체 시스템 메모리 사용량 증가 20% 이내
- [ ] 운영 문서 완성도 확인

**상세 가이드**: [PHASE4_INTEGRATION.md](./PHASE4_INTEGRATION.md)

---

## 예상 효과

### 1. 성능 개선

| 지표 | 현재 | 목표 | 개선율 |
|------|------|------|--------|
| 평균 응답 시간 | 5초 | 2.5초 | 50% ↓ |
| Bitbucket API 호출 | 100회/일 | 30회/일 | 70% ↓ |
| LLM API 비용 | $100/월 | $50/월 | 50% ↓ |

### 2. 운영 효율성

| 지표 | 현재 | 목표 | 개선율 |
|------|------|------|--------|
| 장애 감지 시간 | 30분 | 5분 | 83% ↓ |
| 디버깅 시간 | 2시간 | 1시간 | 50% ↓ |
| 모니터링 커버리지 | 20% | 90% | 350% ↑ |

### 3. 비용 절감

- **LLM API 비용**: 캐싱으로 인한 중복 호출 제거 → 월 $50 절감
- **Bitbucket API 제한**: Rate Limit 여유 확보로 스로틀링 위험 제거
- **운영 인력**: 자동 모니터링 및 알림으로 인한 효율성 증가

### 4. 데이터 기반 의사결정

- **이력 분석**: 가장 많이 처리되는 이슈 타입 파악 → Agent 최적화
- **성능 분석**: 병목 지점 식별 → 우선순위 개선
- **비용 분석**: LLM 토큰 사용 패턴 파악 → 프롬프트 최적화

---

## 리소스 요구사항

### Kubernetes 클러스터

| 컴포넌트 | CPU | 메모리 | 스토리지 | 수량 |
|---------|-----|--------|----------|------|
| Router Agent | 500m | 512Mi | - | 3 Pods |
| SDB Agent | 2000m | 2Gi | - | 2 Pods |
| Redis | 500m | 512Mi | 1Gi | 1 Pod |
| PostgreSQL | 1000m | 1Gi | 10Gi | 1 Pod |
| Prometheus | 1000m | 2Gi | 20Gi | 1 Pod |
| Grafana | 500m | 512Mi | 5Gi | 1 Pod |
| **합계** | **9.5 CPU** | **13Gi** | **36Gi** | **11 Pods** |

### 추가 리소스 (고도화 전 대비)

- **CPU**: +3 CPU (기존 6.5 → 9.5)
- **메모리**: +4Gi (기존 9Gi → 13Gi)
- **스토리지**: +36Gi (신규)

---

## 위험 요소 및 대응 방안

### 1. 리소스 부족
- **위험**: 클러스터 리소스 부족으로 인한 배포 실패
- **대응**: 사전 리소스 확인, 필요시 노드 추가 또는 리소스 요청량 조정

### 2. 데이터 마이그레이션
- **위험**: 기존 운영 중인 시스템에 영향
- **대응**: Blue-Green 배포, Feature Flag를 통한 점진적 적용

### 3. 캐시 무효화
- **위험**: 잘못된 캐시로 인한 오동작
- **대응**: TTL 보수적 설정, 캐시 키 버저닝, 수동 캐시 삭제 도구 제공

### 4. DB 성능 저하
- **위험**: 이력 데이터 증가로 인한 쿼리 성능 저하
- **대응**: 파티셔닝, 아카이빙, 인덱스 최적화

### 5. 모니터링 오버헤드
- **위험**: 메트릭 수집으로 인한 성능 저하
- **대응**: 샘플링 비율 조정, 불필요한 메트릭 제거

---

## 롤백 계획

각 Phase별로 독립적으로 배포되므로 문제 발생 시 해당 Phase만 롤백 가능합니다.

### Phase 1 롤백
```bash
helm uninstall prometheus -n agent-system
helm uninstall grafana -n agent-system
# Agent 코드에서 메트릭 수집 비활성화 (환경 변수)
```

### Phase 2 롤백
```bash
helm uninstall redis -n agent-system
# Agent 코드에서 캐싱 비활성화 (환경 변수)
```

### Phase 3 롤백
```bash
helm uninstall postgresql -n agent-system
# Agent 코드에서 DB 저장 비활성화 (환경 변수)
```

---

## 다음 단계

### 즉시 시작 가능한 작업
1. [PHASE1_MONITORING.md](./PHASE1_MONITORING.md) 검토
2. Prometheus/Grafana Helm 차트 작성
3. Router Agent 메트릭 엔드포인트 구현

### 준비 사항
- [ ] Kubernetes 클러스터 리소스 확인
- [ ] 영구 스토리지 (PV) 준비 확인
- [ ] 개발/스테이징 환경 준비
- [ ] 팀원 교육 계획 수립

### 문서 읽기 순서
1. **OVERVIEW.md** (현재 문서) - 전체 계획 파악
2. **PHASE1_MONITORING.md** - 모니터링 구축
3. **PHASE2_REDIS.md** - 캐싱 통합
4. **DATABASE_SCHEMA.md** - DB 스키마 이해
5. **PHASE3_POSTGRESQL.md** - DB 통합
6. **PHASE4_INTEGRATION.md** - 최종 통합
7. **OPERATIONS_GUIDE.md** - 운영 방법

---

## 참고 자료

### 내부 문서
- [Multi-Agent 아키텍처](../../sdb-agent/doc/MULTI_AGENT_ARCHITECTURE.md)
- [프로세스 플로우](../../sdb-agent/doc/PROCESS_FLOW.md)
- [Kubernetes 배포 가이드](../../MINIKUBE_DEPLOYMENT.md)

### 외부 문서
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Redis Documentation](https://redis.io/docs/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

---

**문서 버전**: 1.0.0
**최종 업데이트**: 2025-10-22
**다음 단계**: [PHASE1_MONITORING.md](./PHASE1_MONITORING.md)
