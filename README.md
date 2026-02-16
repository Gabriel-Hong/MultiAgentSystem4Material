# Jira-Driven Multi-Agent Automation System

> Jira 이슈를 트리거로 C++ 소스코드를 자동 분석/수정하고 Bitbucket Pull Request까지 생성하는 LLM 기반 Multi-Agent 시스템

![System Architecture](docs/images/Entire_Architecture.png)

---

## What I Built

이 프로젝트는 **건설 구조 해석 소프트웨어**의 Material Database 추가 업무를 자동화하기 위해 설계/개발한 시스템입니다.

기존에는 Jira 이슈가 생성되면 개발자가 직접 4개의 C++ 소스 파일을 열어 수십 곳을 수정하고, 수동으로 브랜치를 만들어 PR을 올리는 반복 작업이 필요했습니다. 이 시스템은 **Jira Webhook 수신부터 코드 수정, PR 생성까지 전 과정을 자동화**합니다.

### 핵심 설계 의사결정

| 문제 | 해결 방식 |
|------|-----------|
| 17,000줄 이상의 C++ 파일을 LLM에 전달할 수 없음 | Clang AST로 관련 함수만 추출하여 토큰 50~80% 절감 |
| C++ 파일이 EUC-KR 인코딩으로 LLM 수정 시 깨짐 | Binary I/O + 인코딩 감지/복원 파이프라인 구축 |
| 동일 이슈에 대한 반복적 LLM 호출로 비용 증가 | Redis 기반 다계층 캐싱 (분류 24h, API 5min) |
| Agent 추가 시 시스템 변경 범위가 큼 | MoE(Mixture of Experts) 패턴으로 Agent 독립 배포/확장 |
| 분류 실패 시 잘못된 Agent로 라우팅 | 신뢰도 임계값(0.5) + Graceful Degradation |

---

## Tech Stack

### Backend
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Router Agent | **Python 3.12** / FastAPI 0.109 + Uvicorn (ASGI) | Webhook 수신, Intent Classification, Agent 라우팅 |
| SDB Agent | **Python 3.12** / Flask 3.0 (Docker Container, K8s Deployment) | C++ 코드 수정, Bitbucket PR 생성 |
| LLM | **OpenAI GPT-5** | 이슈 분류, Spec 변환, 코드 Diff 생성 |
| C++ Parser | **libclang** 16.0 (Clang AST) | 함수 단위 코드 추출, 라인 넘버 매핑 |
| Embedding | **sentence-transformers** (all-MiniLM-L6-v2) | 유사 함수 검색 (코사인 유사도) |

### Data & Caching
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Cache | **Redis** 7.2 | LLM 응답 캐싱 (24h), API 응답 캐싱 (5min) |
| Database | **PostgreSQL** 15 | 요청 이력, 분류 결과, 코드 변경 이력, 성능 메트릭 |

### Infrastructure
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Container | **Docker** (Multi-stage, Python 3.12-slim) | 애플리케이션 컨테이너화 |
| Orchestration | **Kubernetes** + **Helm** 3.x | 배포, 스케일링, 서비스 디스커버리 |
| Auto-scaling | **HPA** (Horizontal Pod Autoscaler) | CPU/Memory 기반 자동 스케일링 |
| Monitoring | **Prometheus** + **Grafana** | 메트릭 수집 및 실시간 대시보드 |
| Ingress | **NGINX Ingress Controller** | 외부 트래픽 라우팅, TLS 종료 |

### External Services
| Service | Integration |
|---------|------------|
| **Jira** | Webhook으로 이슈 생성/수정 이벤트 수신 |
| **Bitbucket** | REST API로 파일 조회, 브랜치 생성, 커밋, PR 생성 |
| **OpenAI** | GPT-5 Chat Completion API (JSON 응답 모드) |

---

## System Architecture

### 전체 처리 흐름

```
Jira 이슈 생성
    |
    | Webhook (POST /webhook)
    v
 ┌─────────────────────────────────────────┐
 │          Router Agent (FastAPI)          │
 │                                         │
 │  1. Webhook 페이로드 파싱               │
 │  2. 요청 이력 저장 (PostgreSQL)         │
 │  3. Intent Classification (GPT-5)       │
 │     - Redis 캐시 확인 (24h TTL)         │
 │     - Cache Miss → LLM 호출            │
 │  4. 신뢰도 검증 (threshold: 0.5)       │
 │  5. Agent 헬스체크 (캐싱 30s/10s)      │
 │  6. Agent로 라우팅                      │
 └────────────────┬────────────────────────┘
                  |
                  | POST /process
                  v
 ┌─────────────────────────────────────────┐
 │           SDB Agent (Flask)             │
 │                                         │
 │  1. Jira ADF → Material Spec 변환      │
 │  2. Bitbucket 브랜치 생성               │
 │  3. 대상 C++ 파일 4개 순차 처리:       │
 │     a. 파일 바이너리 조회               │
 │     b. 인코딩 감지 (chardet + 휴리스틱)│
 │     c. Clang AST로 관련 함수 추출      │
 │     d. 구현 가이드 로딩                 │
 │     e. LLM에 Focused Prompt 전송       │
 │     f. JSON Diff 응답 파싱 및 적용     │
 │     g. 원본 인코딩으로 재인코딩         │
 │  4. 멀티파일 원자적 커밋                │
 │  5. Pull Request 생성                   │
 └─────────────────────────────────────────┘
                  |
                  v
 Bitbucket PR 생성 완료 → Jira 이슈 처리 완료
```

### 수정 대상 C++ 파일

| 파일 | 역할 | 처리 방식 |
|------|------|-----------|
| `DBCodeDef.h` | Material 코드 상수 정의 (#define 매크로) | Pragma Region 파싱, 매크로 삽입 |
| `MatlDB.cpp` | Material Enum 및 목록 등록 | Clang AST 함수 추출, Diff 생성 |
| `DBLib.cpp` | Material 기본 DB 설정 | Clang AST 함수 추출, Diff 생성 |
| `DgnDataCtrl.cpp` | 항복강도 계산 로직 | Clang AST 함수 추출, Diff 생성 |

---

## Key Technical Details

### 1. Clang AST 기반 코드 추출

17,000줄 이상의 C++ 파일을 LLM에 통째로 전달하면 토큰 한도를 초과합니다. Clang AST를 사용해 **이슈와 관련된 함수만 정확히 추출**합니다.

```
전체 파일 (17,000줄)
    │
    ├── Clang AST 파싱 (C++17, Windows 매크로 지원)
    │   ├── FUNCTION_DECL 노드 탐색
    │   ├── CXX_METHOD 노드 탐색
    │   └── Content-based 라인 넘버 매핑
    │
    ├── 관련 함수 필터링 (키워드 매칭)
    │
    └── Focused Context 생성 (~500줄)
        ├── 함수 시그니처 + 본문
        ├── 3줄 상위 컨텍스트
        └── 6자리 라인넘버 프리픽스 (예: "   420|")
```

Clang 미설치 환경에서는 정규식 기반 함수 추출로 Fallback

### 2. 인코딩 보존 파이프라인

레거시 C++ 파일의 EUC-KR/CP949 인코딩을 전체 파이프라인에서 보존합니다.

```
바이너리 읽기 → chardet 감지 → Decode → 텍스트 수정 → 원본 인코딩 Encode → 바이너리 커밋
```

- chardet 신뢰도 < 0.95 + 한국어 바이트 감지 시 CP949 강제 적용
- ISO-8859-1 오탐 방지 로직
- BOM (UTF-8/UTF-16) 자동 제거
- Fallback 체인: 감지 인코딩 → UTF-8 → CP949 → EUC-KR → Latin-1

### 3. LLM Diff 생성 전략

LLM이 직접 코드를 수정하는 대신 **구조화된 JSON Diff를 생성**하도록 설계했습니다.

```json
{
  "modifications": [
    {
      "line_start": 420,
      "line_end": 425,
      "action": "replace",
      "old_content": "// 기존 코드 (라인 넘버 없이)",
      "new_content": "// 수정된 코드 (들여쓰기 보존)",
      "description": "변경 사유"
    }
  ],
  "summary": "전체 변경 요약"
}
```

- Diff는 **역순 적용** (라인 오프셋 오류 방지)
- 원본 줄바꿈 스타일 (CRLF/LF) 보존
- `old_content` 정확 매칭으로 잘못된 위치 수정 방지

### 4. 다계층 Redis 캐싱

| 대상 | TTL | 키 패턴 | 효과 |
|------|-----|---------|------|
| Intent Classification | 24시간 | `classification:{SHA256}` | OpenAI API 비용 최대 60% 절감 |
| LLM 코드 생성 | 24시간 | `llm:code:{SHA256}` | 동일 프롬프트 재호출 방지 |
| Bitbucket API | 5분 | `bitbucket:{type}:{ws}:{repo}:...` | Rate Limit 회피 |
| Agent 헬스체크 | 30s/10s | `agent:health:{name}` | 불필요한 헬스체크 감소 |

모든 캐시 연산은 **Graceful Degradation** 적용 - Redis 장애 시 캐싱 없이 정상 동작

### 5. PostgreSQL 이력 관리

4개 테이블로 전체 파이프라인 이력을 영구 저장합니다.

| 테이블 | 저장 내용 |
|--------|-----------|
| `request_history` | Webhook 요청 전체 페이로드, 처리 상태 |
| `classification_history` | 분류된 Agent, 신뢰도, 추론 근거, 캐시 여부 |
| `code_change_history` | 수정 파일, 변경 유형, Diff, 브랜치, PR URL |
| `performance_metrics` | Agent별 처리 시간, LLM 토큰 사용량 |

---

## Observability

### Prometheus 메트릭

**Router Agent**:
- `router_requests_total` - 요청 수 (엔드포인트별, 성공/실패)
- `router_classification_duration_seconds` - 분류 소요 시간 (히스토그램)
- `router_classification_confidence` - 분류 신뢰도 분포
- `router_agent_call_duration_seconds` - Agent 호출 시간
- `cache_hits_total` / `cache_misses_total` - 캐시 히트율

**SDB Agent**:
- `sdb_processing_duration_seconds` - 전체 처리 시간
- `sdb_bitbucket_api_calls_total` - Bitbucket API 호출 수
- `sdb_llm_requests_total` / `sdb_llm_tokens_used_total` - LLM 사용량
- `sdb_pr_created_total` - PR 생성 성공/실패
- `sdb_files_modified_total` - 파일 수정 수

### Grafana 대시보드
- 전체 요청률 및 응답 시간 추이
- Agent별 처리 시간 분포
- 캐시 히트율 그래프
- LLM 토큰 사용량 (비용 추적)
- 에러율 및 상태 코드 분포

---

## Deployment

3가지 배포 환경을 지원합니다.

### 1. Docker Compose (로컬 개발)

```bash
cp env.example .env     # 환경 변수 설정
bash scripts/build-images.sh
bash scripts/deploy-local.sh

# 테스트
curl http://localhost:5000/health
curl http://localhost:5000/agents
```

### 2. Kubernetes - Minikube (로컬 K8s)

```bash
bash scripts/minikube-setup.sh
USE_MINIKUBE=true bash scripts/build-images.sh
bash scripts/deploy-k8s-local.sh

kubectl port-forward svc/router-agent-svc 5000:5000 -n agent-system
```

### 3. Kubernetes - Cloud (Production)

```bash
cp env.example .env && vim .env

export REGISTRY="your-registry.azurecr.io"
export VERSION="1.0.0"

PUSH_IMAGES=1 bash scripts/build-images.sh $VERSION $REGISTRY
REGISTRY=$REGISTRY VERSION=$VERSION bash scripts/deploy-k8s-cloud.sh
```

### 환경별 리소스 설정

| 항목 | Local (Minikube) | Production (Cloud) |
|------|------------------|-------------------|
| Router 복제본 | 1 | 3 (HPA: 3~20) |
| SDB Agent 복제본 | 1 | 2 (HPA: 2~20) |
| Router CPU/Mem | 100m/128Mi | 250m/256Mi |
| SDB Agent CPU/Mem | 250m/256Mi | 500m/512Mi |
| TLS | 비활성화 | Let's Encrypt |
| 모니터링 | 비활성화 | Prometheus + Grafana |
| Network Policy | 비활성화 | 활성화 |

---

## Project Structure

```
GenerateSDBAgent/
├── router-agent/                    # Router Agent (Orchestrator)
│   ├── app/
│   │   ├── main.py                  # FastAPI 앱, Webhook/Health/Metrics 엔드포인트
│   │   ├── intent_classifier.py     # GPT-4 기반 이슈 분류 + Redis 캐싱
│   │   ├── agent_registry.py        # Agent 등록/조회/헬스체크
│   │   ├── cache.py                 # Redis CacheManager (Graceful Degradation)
│   │   ├── db_manager.py            # PostgreSQL 이력 저장 (Connection Pool)
│   │   ├── config.py                # Pydantic Settings (환경 변수)
│   │   ├── metrics.py               # Prometheus 메트릭 정의 및 데코레이터
│   │   └── models.py                # Pydantic 요청/응답 모델
│   ├── Dockerfile
│   └── requirements.txt
│
├── sdb-agent/                       # SDB Agent (Specialized)
│   ├── app/
│   │   ├── main.py                  # Flask 앱, /process /webhook 엔드포인트
│   │   ├── issue_processor.py       # 전체 처리 파이프라인 오케스트레이션
│   │   ├── bitbucket_api.py         # Bitbucket REST API (파일/브랜치/커밋/PR)
│   │   ├── llm_handler.py           # OpenAI GPT-4 코드 Diff 생성 및 적용
│   │   ├── code_chunker.py          # Clang AST 함수 추출 + Regex Fallback
│   │   ├── large_file_handler.py    # 대용량 파일 분할 처리 전략
│   │   ├── encoding_handler.py      # EUC-KR/CP949 인코딩 감지 및 보존
│   │   ├── prompt_builder.py        # Focused/Full-file 프롬프트 빌더
│   │   ├── embedding_search.py      # sentence-transformers 유사도 검색
│   │   ├── cache_manager.py         # Bitbucket/LLM 응답 캐싱 데코레이터
│   │   ├── db_manager.py            # 코드 변경/성능 메트릭 PostgreSQL 저장
│   │   ├── target_files_config.py   # 수정 대상 파일 및 섹션 설정
│   │   ├── config.py                # Pydantic Settings
│   │   └── metrics.py               # Prometheus 메트릭
│   ├── doc/
│   │   ├── guides/                  # 파일별 구현 가이드 (LLM 프롬프트에 포함)
│   │   │   ├── DBCodeDef_guide.md
│   │   │   ├── MatlDB_guide.md
│   │   │   ├── DBLib_guide.md
│   │   │   └── DgnDataCtrl_guide.md
│   │   ├── Spec_File.md             # Material Spec 변환 템플릿
│   │   └── ...                      # 기타 기술 문서
│   ├── test/                        # 테스트 코드
│   ├── few_shot_examples.json       # LLM Few-shot 학습 예시
│   ├── Dockerfile
│   └── requirements.txt
│
├── helm/multi-agent-system/         # Helm Charts
│   ├── Chart.yaml                   # Chart 메타데이터 (v1.0.0)
│   ├── values.yaml                  # 기본 설정값
│   ├── values-local.yaml            # Minikube 오버라이드
│   ├── values-production.yaml       # 프로덕션 오버라이드
│   └── templates/
│       ├── router-agent/            # Deployment, HPA, Service
│       ├── sdb-agent/               # Deployment, HPA, Service
│       ├── redis/                   # Deployment, PVC, Service, ConfigMap
│       ├── postgresql/              # StatefulSet, PVC, Service, Secret, InitScript
│       ├── monitoring/
│       │   ├── prometheus/          # Deployment, ConfigMap, RBAC, PVC
│       │   └── grafana/             # Deployment, Datasource, Dashboard, PVC
│       ├── configmap.yaml
│       ├── secrets.yaml
│       └── ingress.yaml
│
├── scripts/                         # 배포 자동화 스크립트
│   ├── build-images.sh              # Docker 이미지 빌드 (Minikube/Registry 지원)
│   ├── deploy-local.sh              # Docker Compose 배포
│   ├── deploy-k8s-local.sh          # Minikube 배포
│   ├── deploy-k8s-cloud.sh          # 클라우드 K8s 배포
│   ├── create-secrets-from-env.sh   # .env → K8s Secret 자동 생성
│   ├── minikube-setup.sh            # Minikube 초기 설정
│   ├── health-check.sh              # 전체 시스템 헬스체크
│   └── ...
│
├── test/                            # 통합 테스트
├── docker-compose.yml               # 로컬 개발용 Compose
├── docs/                            # 프로젝트 문서
│   ├── images/                      # 아키텍처 다이어그램
│   ├── enhancement/                 # 고도화 가이드
│   ├── kubernetes/                  # K8s 배포 가이드
│   ├── monitoring/                  # 모니터링 가이드
│   ├── redis/                       # Redis 설정 가이드
│   ├── postgresql/                  # PostgreSQL 가이드
│   └── configuration/              # 환경 변수 설정 가이드
└── env.example                      # 환경 변수 예시
```

---

## Design Patterns & Architecture Decisions

| 패턴 | 적용 위치 | 이유 |
|------|-----------|------|
| **MoE (Mixture of Experts)** | 전체 시스템 | Agent별 독립 배포/스케일링, 새 Agent 추가 시 기존 코드 변경 최소화 |
| **Graceful Degradation** | Redis, PostgreSQL | 캐시/DB 장애 시에도 핵심 기능(코드 수정, PR 생성) 정상 동작 |
| **Decorator Pattern** | Prometheus 메트릭 | 비즈니스 로직과 메트릭 수집 분리, 비침투적 계측 |
| **Connection Pool** | PostgreSQL | ThreadedConnectionPool(1~10)으로 동시 요청 처리 |
| **Binary I/O Pipeline** | Bitbucket 파일 처리 | 인코딩 변환 없이 원본 바이트 보존 |
| **Reverse Diff Application** | LLM 코드 수정 | 라인 오프셋 누적 오류 방지 |
| **Differentiated TTL** | Agent 헬스체크 캐시 | 정상(30s)/비정상(10s)으로 장애 복구 감지 속도 차별화 |
| **Stateless Service** | 모든 Agent | 수평 확장 가능, HPA와 호환 |

---

## Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-your-api-key
BITBUCKET_ACCESS_TOKEN=your-token
BITBUCKET_WORKSPACE=your-workspace
BITBUCKET_REPOSITORY=your-repository

# Optional (defaults provided)
OPENAI_MODEL=gpt-5                         # LLM 모델
CLASSIFICATION_CONFIDENCE_THRESHOLD=0.5    # 분류 신뢰도 임계값
REDIS_HOST=redis                           # Redis 호스트
REDIS_PORT=6379
DB_HOST=postgresql                         # PostgreSQL 호스트
DB_PORT=5432
DB_NAME=agent_system
DB_USER=agent_user
DB_PASSWORD=postgres123
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| **v1.1.0** | 2025-11-04 | Redis 캐싱, PostgreSQL 이력 관리, Prometheus + Grafana 모니터링, Pydantic Settings |
| **v1.0.0** | 2025-10-16 | Multi-Agent 기본 아키텍처 구현, Router/SDB Agent, Helm Chart, Docker Compose |

---

## Documentation

| 문서 | 설명 |
|------|------|
| [Router Agent README](router-agent/README.md) | Router Agent 상세 API 및 구현 |
| [SDB Agent README](sdb-agent/README.md) | SDB Agent 처리 파이프라인 상세 |
| [고도화 Overview](docs/enhancement/OVERVIEW.md) | Redis, PostgreSQL, 모니터링 고도화 상세 |
| [모니터링 가이드](docs/monitoring/README.md) | Prometheus + Grafana 설정 |
| [K8s 배포 가이드](docs/kubernetes/MINIKUBE_DEPLOYMENT.md) | Minikube/Cloud 배포 절차 |
| [환경 변수 가이드](docs/configuration/README.md) | 환경 변수 설정 흐름 |
| [프로세스 플로우](sdb-agent/doc/PROCESS_FLOW.md) | SDB Agent 처리 흐름 상세 |
| [인코딩 처리](sdb-agent/doc/ENCODING_FIX_GUIDE.md) | EUC-KR 인코딩 보존 전략 |
| [대용량 파일 전략](sdb-agent/doc/LARGE_FILE_STRATEGY.md) | 17,000줄+ 파일 처리 방법 |
| [Clang AST 가이드](sdb-agent/doc/CLANG_AST_GUIDE.md) | C++ 코드 파싱 구현 |

---

## License

MIT License
