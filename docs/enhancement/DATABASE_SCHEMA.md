# PostgreSQL 데이터베이스 스키마

## 문서 정보
- **버전**: 1.0.0
- **작성일**: 2025-10-22
- **데이터베이스**: PostgreSQL 15+

---

## 목차
1. [개요](#개요)
2. [ERD](#erd)
3. [테이블 상세](#테이블-상세)
4. [인덱스 전략](#인덱스-전략)
5. [파티셔닝 전략](#파티셔닝-전략)
6. [쿼리 예시](#쿼리-예시)
7. [마이그레이션](#마이그레이션)

---

## 개요

### 목적
- 모든 요청/응답 이력 저장
- Intent Classification 결과 분석
- 코드 변경 이력 추적
- 성능 메트릭 수집 및 분석

### 데이터 보관 정책
- **이력 데이터**: 6개월 보관 후 아카이브
- **성능 메트릭**: 3개월 보관 후 집계/삭제
- **실시간 조회**: 최근 1개월 데이터만 인덱스

---

## ERD

```
┌──────────────────────┐
│  request_history     │
│──────────────────────│
│ id (PK)              │◄───┐
│ issue_key            │    │
│ webhook_event        │    │
│ payload (JSONB)      │    │
│ status               │    │
│ created_at           │    │
│ updated_at           │    │
└──────────────────────┘    │
                             │
                             │ FK
┌──────────────────────────┐│
│ classification_history   ││
│──────────────────────────││
│ id (PK)                  ││
│ request_id (FK) ─────────┘
│ issue_key                │
│ classified_agent         │
│ confidence               │
│ reasoning                │
│ cached                   │
│ created_at               │
└──────────────────────────┘
           │
           │ FK
┌──────────────────────────┐│
│ code_change_history      ││
│──────────────────────────││
│ id (PK)                  ││
│ request_id (FK) ─────────┘
│ issue_key                │
│ file_path                │
│ change_type              │
│ diff_content (TEXT)      │
│ branch_name              │
│ pr_url                   │
│ created_at               │
└──────────────────────────┘
           │
           │ FK
┌──────────────────────────┐│
│ performance_metrics      ││
│──────────────────────────││
│ id (PK)                  ││
│ request_id (FK) ─────────┘
│ agent_name               │
│ metric_type              │
│ metric_value             │
│ metadata (JSONB)         │
│ created_at               │
└──────────────────────────┘
```

---

## 테이블 상세

### 1. request_history

**목적**: 모든 Webhook 요청 및 처리 결과 저장

```sql
CREATE TABLE request_history (
    -- 기본 키
    id SERIAL PRIMARY KEY,

    -- Jira 이슈 정보
    issue_key VARCHAR(50) NOT NULL,
    webhook_event VARCHAR(50),  -- 'jira:issue_created', 'jira:issue_updated' 등

    -- 요청 페이로드 (전체 JSON 저장)
    payload JSONB NOT NULL,

    -- 처리 상태
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, processing, completed, failed

    -- 타임스탬프
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 코멘트
COMMENT ON TABLE request_history IS 'Webhook 요청 이력';
COMMENT ON COLUMN request_history.issue_key IS 'Jira 이슈 키 (예: PROJ-123)';
COMMENT ON COLUMN request_history.payload IS 'Jira Webhook 전체 페이로드 (JSON)';
COMMENT ON COLUMN request_history.status IS '처리 상태: pending, processing, completed, failed';
```

**컬럼 상세**:

| 컬럼 | 타입 | NULL | 기본값 | 설명 |
|------|------|------|--------|------|
| id | SERIAL | NO | AUTO | 기본 키 |
| issue_key | VARCHAR(50) | NO | - | Jira 이슈 키 |
| webhook_event | VARCHAR(50) | YES | NULL | Webhook 이벤트 타입 |
| payload | JSONB | NO | - | 전체 Webhook 페이로드 |
| status | VARCHAR(20) | NO | 'pending' | 처리 상태 |
| created_at | TIMESTAMP | NO | NOW() | 생성 시각 |
| updated_at | TIMESTAMP | NO | NOW() | 수정 시각 |

**샘플 데이터**:

```sql
INSERT INTO request_history (issue_key, webhook_event, payload, status)
VALUES (
    'PROJ-123',
    'jira:issue_created',
    '{
        "issue": {
            "key": "PROJ-123",
            "fields": {
                "summary": "SDB 개발 요청: 신규 재질 추가",
                "issuetype": {"name": "Task"}
            }
        }
    }'::JSONB,
    'completed'
);
```

---

### 2. classification_history

**목적**: Intent Classification 결과 저장 및 분석

```sql
CREATE TABLE classification_history (
    -- 기본 키
    id SERIAL PRIMARY KEY,

    -- 외래 키
    request_id INTEGER REFERENCES request_history(id) ON DELETE CASCADE,

    -- 분류 정보
    issue_key VARCHAR(50) NOT NULL,
    classified_agent VARCHAR(50) NOT NULL,  -- 'sdb-agent', 'code-review-agent' 등
    confidence DECIMAL(3, 2) NOT NULL,  -- 0.00 ~ 1.00
    reasoning TEXT,  -- 분류 이유 (LLM의 설명)

    -- 캐시 여부
    cached BOOLEAN NOT NULL DEFAULT FALSE,

    -- 타임스탬프
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 코멘트
COMMENT ON TABLE classification_history IS 'Intent Classification 결과 이력';
COMMENT ON COLUMN classification_history.confidence IS '분류 신뢰도 (0.00 ~ 1.00)';
COMMENT ON COLUMN classification_history.cached IS '캐시된 결과인지 여부';
```

**컬럼 상세**:

| 컬럼 | 타입 | NULL | 기본값 | 설명 |
|------|------|------|--------|------|
| id | SERIAL | NO | AUTO | 기본 키 |
| request_id | INTEGER | YES | NULL | 요청 이력 참조 |
| issue_key | VARCHAR(50) | NO | - | Jira 이슈 키 |
| classified_agent | VARCHAR(50) | NO | - | 선택된 Agent 이름 |
| confidence | DECIMAL(3,2) | NO | - | 신뢰도 (0.00~1.00) |
| reasoning | TEXT | YES | NULL | 분류 이유 |
| cached | BOOLEAN | NO | FALSE | 캐시 사용 여부 |
| created_at | TIMESTAMP | NO | NOW() | 생성 시각 |

**샘플 데이터**:

```sql
INSERT INTO classification_history (request_id, issue_key, classified_agent, confidence, reasoning, cached)
VALUES (
    1,
    'PROJ-123',
    'sdb-agent',
    0.95,
    'SDB 개발 요청 키워드가 포함되어 있고, 재질 추가 작업으로 판단됨',
    FALSE
);
```

---

### 3. code_change_history

**목적**: 코드 변경 이력 추적 (파일별)

```sql
CREATE TABLE code_change_history (
    -- 기본 키
    id SERIAL PRIMARY KEY,

    -- 외래 키
    request_id INTEGER REFERENCES request_history(id) ON DELETE CASCADE,

    -- 변경 정보
    issue_key VARCHAR(50) NOT NULL,
    file_path TEXT NOT NULL,  -- 변경된 파일 경로
    change_type VARCHAR(20) NOT NULL,  -- 'added', 'modified', 'deleted'
    diff_content TEXT,  -- unified diff 형식

    -- Git 정보
    branch_name VARCHAR(100),
    commit_hash VARCHAR(40),  -- Git commit SHA
    pr_url TEXT,  -- Pull Request URL

    -- 타임스탬프
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 코멘트
COMMENT ON TABLE code_change_history IS '코드 변경 이력';
COMMENT ON COLUMN code_change_history.change_type IS '변경 유형: added, modified, deleted';
COMMENT ON COLUMN code_change_history.diff_content IS 'Unified diff 형식의 변경 내용';
```

**컬럼 상세**:

| 컬럼 | 타입 | NULL | 기본값 | 설명 |
|------|------|------|--------|------|
| id | SERIAL | NO | AUTO | 기본 키 |
| request_id | INTEGER | YES | NULL | 요청 이력 참조 |
| issue_key | VARCHAR(50) | NO | - | Jira 이슈 키 |
| file_path | TEXT | NO | - | 파일 경로 |
| change_type | VARCHAR(20) | NO | - | 변경 유형 |
| diff_content | TEXT | YES | NULL | Diff 내용 |
| branch_name | VARCHAR(100) | YES | NULL | 브랜치 이름 |
| commit_hash | VARCHAR(40) | YES | NULL | Commit SHA |
| pr_url | TEXT | YES | NULL | PR URL |
| created_at | TIMESTAMP | NO | NOW() | 생성 시각 |

**샘플 데이터**:

```sql
INSERT INTO code_change_history (
    request_id, issue_key, file_path, change_type,
    diff_content, branch_name, pr_url
)
VALUES (
    1,
    'PROJ-123',
    'src/DBLib/MatlDB.cpp',
    'modified',
    E'--- a/src/DBLib/MatlDB.cpp\n+++ b/src/DBLib/MatlDB.cpp\n@@ -100,6 +100,10 @@\n+    // 신규 재질 추가\n+    AddMaterial("NewMaterial", 210000, 0.3);',
    'feature/PROJ-123-add-material',
    'https://bitbucket.org/workspace/repo/pull-requests/42'
);
```

---

### 4. performance_metrics

**목적**: 성능 메트릭 수집 (처리 시간, LLM 토큰 사용량 등)

```sql
CREATE TABLE performance_metrics (
    -- 기본 키
    id SERIAL PRIMARY KEY,

    -- 외래 키
    request_id INTEGER REFERENCES request_history(id) ON DELETE CASCADE,

    -- 메트릭 정보
    agent_name VARCHAR(50) NOT NULL,  -- 'router-agent', 'sdb-agent'
    metric_type VARCHAR(50) NOT NULL,  -- 'latency', 'llm_tokens', 'api_calls' 등
    metric_value DECIMAL(10, 2) NOT NULL,

    -- 추가 메타데이터 (JSON)
    metadata JSONB,

    -- 타임스탬프
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 코멘트
COMMENT ON TABLE performance_metrics IS '성능 메트릭';
COMMENT ON COLUMN performance_metrics.metric_type IS '메트릭 유형: latency, llm_tokens, api_calls 등';
COMMENT ON COLUMN performance_metrics.metadata IS '추가 정보 (JSON)';
```

**컬럼 상세**:

| 컬럼 | 타입 | NULL | 기본값 | 설명 |
|------|------|------|--------|------|
| id | SERIAL | NO | AUTO | 기본 키 |
| request_id | INTEGER | YES | NULL | 요청 이력 참조 |
| agent_name | VARCHAR(50) | NO | - | Agent 이름 |
| metric_type | VARCHAR(50) | NO | - | 메트릭 유형 |
| metric_value | DECIMAL(10,2) | NO | - | 메트릭 값 |
| metadata | JSONB | YES | NULL | 추가 정보 |
| created_at | TIMESTAMP | NO | NOW() | 생성 시각 |

**메트릭 유형**:

| metric_type | 설명 | metric_value 단위 | metadata 예시 |
|-------------|------|------------------|--------------|
| latency | 처리 시간 | 초 (seconds) | `{"component": "classification"}` |
| llm_tokens | LLM 토큰 사용량 | 개수 | `{"model": "gpt-4", "type": "prompt"}` |
| api_calls | API 호출 횟수 | 개수 | `{"api": "bitbucket", "endpoint": "get_file"}` |
| cache_hit_rate | 캐시 히트율 | 퍼센트 (%) | `{"cache_type": "classification"}` |

**샘플 데이터**:

```sql
-- 처리 시간
INSERT INTO performance_metrics (request_id, agent_name, metric_type, metric_value, metadata)
VALUES (1, 'sdb-agent', 'latency', 8.5, '{"component": "code_generation"}'::JSONB);

-- LLM 토큰 사용량
INSERT INTO performance_metrics (request_id, agent_name, metric_type, metric_value, metadata)
VALUES (1, 'sdb-agent', 'llm_tokens', 1250, '{"model": "gpt-4", "type": "prompt"}'::JSONB);

-- API 호출 횟수
INSERT INTO performance_metrics (request_id, agent_name, metric_type, metric_value, metadata)
VALUES (1, 'sdb-agent', 'api_calls', 5, '{"api": "bitbucket", "cached": 2}'::JSONB);
```

---

## 인덱스 전략

### 주요 조회 패턴
1. **이슈 키로 조회**: `SELECT * FROM request_history WHERE issue_key = 'PROJ-123'`
2. **날짜 범위 조회**: `SELECT * FROM request_history WHERE created_at BETWEEN ... AND ...`
3. **Agent별 집계**: `SELECT agent_name, COUNT(*) FROM classification_history GROUP BY agent_name`
4. **성능 분석**: `SELECT AVG(metric_value) FROM performance_metrics WHERE metric_type = 'latency'`

### 인덱스 정의

```sql
-- request_history 인덱스
CREATE INDEX idx_request_history_issue_key ON request_history(issue_key);
CREATE INDEX idx_request_history_created_at ON request_history(created_at DESC);
CREATE INDEX idx_request_history_status ON request_history(status) WHERE status != 'completed';  -- 부분 인덱스

-- classification_history 인덱스
CREATE INDEX idx_classification_history_request_id ON classification_history(request_id);
CREATE INDEX idx_classification_history_agent ON classification_history(classified_agent);
CREATE INDEX idx_classification_history_created_at ON classification_history(created_at DESC);
CREATE INDEX idx_classification_history_confidence ON classification_history(confidence) WHERE confidence < 0.7;  -- 낮은 신뢰도만

-- code_change_history 인덱스
CREATE INDEX idx_code_change_history_request_id ON code_change_history(request_id);
CREATE INDEX idx_code_change_history_issue_key ON code_change_history(issue_key);
CREATE INDEX idx_code_change_history_file_path ON code_change_history(file_path);
CREATE INDEX idx_code_change_history_created_at ON code_change_history(created_at DESC);

-- performance_metrics 인덱스
CREATE INDEX idx_performance_metrics_request_id ON performance_metrics(request_id);
CREATE INDEX idx_performance_metrics_agent_type ON performance_metrics(agent_name, metric_type);
CREATE INDEX idx_performance_metrics_created_at ON performance_metrics(created_at DESC);

-- JSONB 인덱스 (payload 검색 최적화)
CREATE INDEX idx_request_history_payload_gin ON request_history USING GIN (payload);
CREATE INDEX idx_performance_metrics_metadata_gin ON performance_metrics USING GIN (metadata);
```

---

## 파티셔닝 전략

대량 데이터가 예상되는 테이블은 월별 파티셔닝 적용

### request_history 파티셔닝

```sql
-- 기존 테이블을 파티션드 테이블로 변환
CREATE TABLE request_history_partitioned (
    LIKE request_history INCLUDING ALL
) PARTITION BY RANGE (created_at);

-- 월별 파티션 생성 (예시: 2025년 1월~6월)
CREATE TABLE request_history_2025_01 PARTITION OF request_history_partitioned
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE request_history_2025_02 PARTITION OF request_history_partitioned
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');

-- ... 이하 생략 ...

-- 자동 파티션 생성 함수 (pg_partman 확장 사용)
CREATE EXTENSION pg_partman;

SELECT create_parent(
    p_parent_table => 'public.request_history_partitioned',
    p_control => 'created_at',
    p_type => 'native',
    p_interval => 'monthly',
    p_premake => 3  -- 3개월 미리 생성
);
```

---

## 쿼리 예시

### 1. 이슈 처리 이력 전체 조회

```sql
SELECT
    rh.id,
    rh.issue_key,
    rh.status,
    rh.created_at,
    ch.classified_agent,
    ch.confidence,
    COUNT(cch.id) AS files_changed,
    AVG(pm.metric_value) FILTER (WHERE pm.metric_type = 'latency') AS avg_latency
FROM request_history rh
LEFT JOIN classification_history ch ON rh.id = ch.request_id
LEFT JOIN code_change_history cch ON rh.id = cch.request_id
LEFT JOIN performance_metrics pm ON rh.id = pm.request_id
WHERE rh.issue_key = 'PROJ-123'
GROUP BY rh.id, ch.id
ORDER BY rh.created_at DESC;
```

### 2. Agent별 처리 건수 및 평균 신뢰도

```sql
SELECT
    classified_agent,
    COUNT(*) AS total_requests,
    AVG(confidence) AS avg_confidence,
    COUNT(*) FILTER (WHERE cached = TRUE) AS cached_count,
    COUNT(*) FILTER (WHERE cached = FALSE) AS non_cached_count
FROM classification_history
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY classified_agent
ORDER BY total_requests DESC;
```

### 3. 가장 많이 수정된 파일 Top 10

```sql
SELECT
    file_path,
    COUNT(*) AS change_count,
    COUNT(DISTINCT issue_key) AS issue_count,
    MAX(created_at) AS last_modified
FROM code_change_history
WHERE created_at >= NOW() - INTERVAL '90 days'
GROUP BY file_path
ORDER BY change_count DESC
LIMIT 10;
```

### 4. LLM 토큰 사용량 집계 (일별)

```sql
SELECT
    DATE(created_at) AS date,
    agent_name,
    SUM(metric_value) AS total_tokens,
    AVG(metric_value) AS avg_tokens_per_request
FROM performance_metrics
WHERE metric_type = 'llm_tokens'
    AND created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at), agent_name
ORDER BY date DESC, total_tokens DESC;
```

### 5. 낮은 신뢰도 분류 결과 조회

```sql
SELECT
    ch.issue_key,
    ch.classified_agent,
    ch.confidence,
    ch.reasoning,
    rh.status,
    rh.created_at
FROM classification_history ch
JOIN request_history rh ON ch.request_id = rh.id
WHERE ch.confidence < 0.7
    AND ch.created_at >= NOW() - INTERVAL '7 days'
ORDER BY ch.confidence ASC;
```

---

## 마이그레이션

### 초기 스키마 생성 스크립트

**파일**: `helm/multi-agent-system/templates/postgresql/init-schema.sql`

```sql
-- 데이터베이스 생성 (필요시)
-- CREATE DATABASE agent_system;

-- 확장 설치
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;  -- 쿼리 통계
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- 텍스트 검색

-- 1. request_history 테이블
CREATE TABLE request_history (
    id SERIAL PRIMARY KEY,
    issue_key VARCHAR(50) NOT NULL,
    webhook_event VARCHAR(50),
    payload JSONB NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_request_history_issue_key ON request_history(issue_key);
CREATE INDEX idx_request_history_created_at ON request_history(created_at DESC);
CREATE INDEX idx_request_history_status ON request_history(status) WHERE status != 'completed';
CREATE INDEX idx_request_history_payload_gin ON request_history USING GIN (payload);

COMMENT ON TABLE request_history IS 'Webhook 요청 이력';

-- 2. classification_history 테이블
CREATE TABLE classification_history (
    id SERIAL PRIMARY KEY,
    request_id INTEGER REFERENCES request_history(id) ON DELETE CASCADE,
    issue_key VARCHAR(50) NOT NULL,
    classified_agent VARCHAR(50) NOT NULL,
    confidence DECIMAL(3, 2) NOT NULL,
    reasoning TEXT,
    cached BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_classification_history_request_id ON classification_history(request_id);
CREATE INDEX idx_classification_history_agent ON classification_history(classified_agent);
CREATE INDEX idx_classification_history_created_at ON classification_history(created_at DESC);
CREATE INDEX idx_classification_history_confidence ON classification_history(confidence) WHERE confidence < 0.7;

COMMENT ON TABLE classification_history IS 'Intent Classification 결과 이력';

-- 3. code_change_history 테이블
CREATE TABLE code_change_history (
    id SERIAL PRIMARY KEY,
    request_id INTEGER REFERENCES request_history(id) ON DELETE CASCADE,
    issue_key VARCHAR(50) NOT NULL,
    file_path TEXT NOT NULL,
    change_type VARCHAR(20) NOT NULL,
    diff_content TEXT,
    branch_name VARCHAR(100),
    commit_hash VARCHAR(40),
    pr_url TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_code_change_history_request_id ON code_change_history(request_id);
CREATE INDEX idx_code_change_history_issue_key ON code_change_history(issue_key);
CREATE INDEX idx_code_change_history_file_path ON code_change_history(file_path);
CREATE INDEX idx_code_change_history_created_at ON code_change_history(created_at DESC);

COMMENT ON TABLE code_change_history IS '코드 변경 이력';

-- 4. performance_metrics 테이블
CREATE TABLE performance_metrics (
    id SERIAL PRIMARY KEY,
    request_id INTEGER REFERENCES request_history(id) ON DELETE CASCADE,
    agent_name VARCHAR(50) NOT NULL,
    metric_type VARCHAR(50) NOT NULL,
    metric_value DECIMAL(10, 2) NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_performance_metrics_request_id ON performance_metrics(request_id);
CREATE INDEX idx_performance_metrics_agent_type ON performance_metrics(agent_name, metric_type);
CREATE INDEX idx_performance_metrics_created_at ON performance_metrics(created_at DESC);
CREATE INDEX idx_performance_metrics_metadata_gin ON performance_metrics USING GIN (metadata);

COMMENT ON TABLE performance_metrics IS '성능 메트릭';

-- Trigger: updated_at 자동 업데이트
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_request_history_updated_at
    BEFORE UPDATE ON request_history
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 샘플 데이터 (개발 환경용)
-- INSERT INTO ... (생략)
```

### 마이그레이션 버전 관리

**권장 도구**: [Flyway](https://flywaydb.org/) 또는 [Liquibase](https://www.liquibase.org/)

**예시**: Flyway 마이그레이션 스크립트

```
db/migration/
├── V1__initial_schema.sql
├── V2__add_commit_hash_column.sql
└── V3__add_partitioning.sql
```

---

**문서 버전**: 1.0.0
**최종 업데이트**: 2025-10-22
**관련 문서**: [PHASE3_POSTGRESQL.md](./PHASE3_POSTGRESQL.md)
