# Phase 3: PostgreSQL 이력 관리

## 문서 정보
- **Phase**: 3 / 4
- **예상 기간**: 1주 (Week 5)
- **난이도**: ⭐⭐⭐⭐⭐ (상)
- **선행 요구사항**: Phase 1, 2 완료

---

## 목차
1. [개요](#개요)
2. [PostgreSQL 배포](#postgresql-배포)
3. [DB Manager 구현](#db-manager-구현)
4. [Router Agent 통합](#router-agent-통합)
5. [SDB Agent 통합](#sdb-agent-통합)
6. [백업 및 복구](#백업-및-복구)
7. [성능 최적화](#성능-최적화)
8. [테스트 및 검증](#테스트-및-검증)
9. [트러블슈팅](#트러블슈팅)

---

## 개요

### 목표
- 모든 요청/응답 이력 영구 저장
- Classification 결과 분석 데이터 확보
- 코드 변경 이력 추적
- 성능 메트릭 데이터 분석 기반 마련

### 저장 데이터

| 테이블 | 목적 | 예상 증가율 |
|-------|------|-----------|
| request_history | Webhook 요청 이력 | 100건/일 |
| classification_history | 분류 결과 이력 | 100건/일 |
| code_change_history | 코드 변경 이력 | 300건/일 (파일별) |
| performance_metrics | 성능 메트릭 | 500건/일 |

**참고**: [DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md) 참조

---

## PostgreSQL 배포

### 1. PostgreSQL ConfigMap

**파일**: `helm/multi-agent-system/templates/postgresql/configmap.yaml`

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: postgresql-config
  namespace: {{ .Values.global.namespace }}
  labels:
    app: postgresql
data:
  POSTGRES_DB: agent_system
  POSTGRES_USER: agent_user
  # POSTGRES_PASSWORD는 Secret으로 관리

  # PostgreSQL 설정
  postgresql.conf: |
    # 연결
    max_connections = 100
    shared_buffers = 256MB

    # 쿼리 플래너
    effective_cache_size = 1GB
    random_page_cost = 1.1  # SSD 기준

    # WAL (Write-Ahead Log)
    wal_level = replica
    max_wal_size = 1GB
    min_wal_size = 80MB

    # 체크포인트
    checkpoint_completion_target = 0.9
    checkpoint_timeout = 10min

    # 로깅
    log_destination = 'stderr'
    logging_collector = on
    log_directory = '/var/log/postgresql'
    log_filename = 'postgresql-%Y-%m-%d.log'
    log_statement = 'ddl'  # DDL 문만 로깅
    log_min_duration_statement = 1000  # 1초 이상 쿼리 로깅

    # 통계
    track_activities = on
    track_counts = on
    track_io_timing = on
    track_functions = all
```

### 2. PostgreSQL Secret

**파일**: `helm/multi-agent-system/templates/postgresql/secret.yaml`

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: postgresql-secret
  namespace: {{ .Values.global.namespace }}
type: Opaque
data:
  # Base64 인코딩된 비밀번호
  # echo -n 'your-strong-password' | base64
  POSTGRES_PASSWORD: {{ .Values.postgresql.password | b64enc | quote }}
```

### 3. PostgreSQL StatefulSet

**파일**: `helm/multi-agent-system/templates/postgresql/statefulset.yaml`

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgresql
  namespace: {{ .Values.global.namespace }}
  labels:
    app: postgresql
spec:
  serviceName: postgresql
  replicas: 1
  selector:
    matchLabels:
      app: postgresql
  template:
    metadata:
      labels:
        app: postgresql
    spec:
      containers:
        - name: postgresql
          image: postgres:15-alpine
          ports:
            - containerPort: 5432
              name: postgresql
          env:
            - name: POSTGRES_DB
              valueFrom:
                configMapKeyRef:
                  name: postgresql-config
                  key: POSTGRES_DB
            - name: POSTGRES_USER
              valueFrom:
                configMapKeyRef:
                  name: postgresql-config
                  key: POSTGRES_USER
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: postgresql-secret
                  key: POSTGRES_PASSWORD
            - name: PGDATA
              value: /var/lib/postgresql/data/pgdata
          volumeMounts:
            - name: data
              mountPath: /var/lib/postgresql/data
            - name: config
              mountPath: /etc/postgresql/postgresql.conf
              subPath: postgresql.conf
            - name: init-scripts
              mountPath: /docker-entrypoint-initdb.d
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
            limits:
              cpu: 1000m
              memory: 1Gi
          livenessProbe:
            exec:
              command:
                - /bin/sh
                - -c
                - pg_isready -U $POSTGRES_USER -d $POSTGRES_DB
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            exec:
              command:
                - /bin/sh
                - -c
                - pg_isready -U $POSTGRES_USER -d $POSTGRES_DB
            initialDelaySeconds: 5
            periodSeconds: 5
      volumes:
        - name: config
          configMap:
            name: postgresql-config
        - name: init-scripts
          configMap:
            name: postgresql-init-scripts
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 10Gi
        {{- if .Values.postgresql.storageClassName }}
        storageClassName: {{ .Values.postgresql.storageClassName }}
        {{- end }}
```

### 4. PostgreSQL Service

**파일**: `helm/multi-agent-system/templates/postgresql/service.yaml`

```yaml
apiVersion: v1
kind: Service
metadata:
  name: postgresql
  namespace: {{ .Values.global.namespace }}
  labels:
    app: postgresql
spec:
  type: ClusterIP
  clusterIP: None  # Headless service for StatefulSet
  ports:
    - port: 5432
      targetPort: 5432
      protocol: TCP
      name: postgresql
  selector:
    app: postgresql
```

### 5. 초기화 스크립트 ConfigMap

**파일**: `helm/multi-agent-system/templates/postgresql/init-scripts-configmap.yaml`

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: postgresql-init-scripts
  namespace: {{ .Values.global.namespace }}
data:
  01-init-schema.sql: |
    -- 확장 설치
    CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
    CREATE EXTENSION IF NOT EXISTS pg_trgm;

    -- 스키마 생성 (DATABASE_SCHEMA.md 참조)
    CREATE TABLE request_history (
        id SERIAL PRIMARY KEY,
        issue_key VARCHAR(50) NOT NULL,
        webhook_event VARCHAR(50),
        payload JSONB NOT NULL,
        status VARCHAR(20) NOT NULL DEFAULT 'pending',
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
    );

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

    CREATE TABLE performance_metrics (
        id SERIAL PRIMARY KEY,
        request_id INTEGER REFERENCES request_history(id) ON DELETE CASCADE,
        agent_name VARCHAR(50) NOT NULL,
        metric_type VARCHAR(50) NOT NULL,
        metric_value DECIMAL(10, 2) NOT NULL,
        metadata JSONB,
        created_at TIMESTAMP NOT NULL DEFAULT NOW()
    );

    -- 인덱스 생성
    CREATE INDEX idx_request_history_issue_key ON request_history(issue_key);
    CREATE INDEX idx_request_history_created_at ON request_history(created_at DESC);
    CREATE INDEX idx_request_history_status ON request_history(status) WHERE status != 'completed';
    CREATE INDEX idx_request_history_payload_gin ON request_history USING GIN (payload);

    CREATE INDEX idx_classification_history_request_id ON classification_history(request_id);
    CREATE INDEX idx_classification_history_agent ON classification_history(classified_agent);
    CREATE INDEX idx_classification_history_created_at ON classification_history(created_at DESC);

    CREATE INDEX idx_code_change_history_request_id ON code_change_history(request_id);
    CREATE INDEX idx_code_change_history_issue_key ON code_change_history(issue_key);
    CREATE INDEX idx_code_change_history_file_path ON code_change_history(file_path);

    CREATE INDEX idx_performance_metrics_agent_type ON performance_metrics(agent_name, metric_type);
    CREATE INDEX idx_performance_metrics_created_at ON performance_metrics(created_at DESC);

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
```

---

## DB Manager 구현

### Router Agent DB Manager

**파일**: `router-agent/app/db.py` (신규)

```python
"""
PostgreSQL 데이터베이스 매니저 - Router Agent
"""
import psycopg2
from psycopg2.extras import Json, RealDictCursor
from psycopg2.pool import ThreadedConnectionPool
from typing import Optional, Dict, Any, List
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseManager:
    """PostgreSQL 데이터베이스 매니저"""

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        min_conn: int = 1,
        max_conn: int = 10
    ):
        """
        Args:
            host: DB 호스트
            port: DB 포트
            database: 데이터베이스 이름
            user: 사용자
            password: 비밀번호
            min_conn: 최소 연결 수
            max_conn: 최대 연결 수
        """
        try:
            self.pool = ThreadedConnectionPool(
                minconn=min_conn,
                maxconn=max_conn,
                host=host,
                port=port,
                database=database,
                user=user,
                password=password
            )
            logger.info(f"DB 연결 풀 생성 성공: {host}:{port}/{database}")
            self.enabled = True
        except Exception as e:
            logger.error(f"DB 연결 실패: {str(e)}")
            logger.warning("이력 저장이 비활성화됩니다.")
            self.enabled = False
            self.pool = None

    @contextmanager
    def get_connection(self):
        """연결 풀에서 연결 가져오기 (context manager)"""
        if not self.enabled:
            yield None
            return

        conn = None
        try:
            conn = self.pool.getconn()
            yield conn
        finally:
            if conn:
                self.pool.putconn(conn)

    def create_request(self, issue_key: str, webhook_event: str, payload: Dict) -> Optional[int]:
        """
        요청 이력 생성

        Args:
            issue_key: Jira 이슈 키
            webhook_event: Webhook 이벤트
            payload: 전체 페이로드

        Returns:
            생성된 request_id 또는 None
        """
        if not self.enabled:
            return None

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO request_history (issue_key, webhook_event, payload, status)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id
                        """,
                        (issue_key, webhook_event, Json(payload), 'processing')
                    )
                    request_id = cur.fetchone()[0]
                    conn.commit()
                    logger.info(f"요청 이력 생성: {issue_key} (ID: {request_id})")
                    return request_id
        except Exception as e:
            logger.error(f"요청 이력 생성 실패: {str(e)}")
            return None

    def update_request_status(self, request_id: int, status: str) -> bool:
        """
        요청 상태 업데이트

        Args:
            request_id: 요청 ID
            status: 상태 (pending, processing, completed, failed)

        Returns:
            성공 여부
        """
        if not self.enabled:
            return False

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE request_history SET status = %s WHERE id = %s",
                        (status, request_id)
                    )
                    conn.commit()
                    logger.debug(f"요청 상태 업데이트: {request_id} → {status}")
                    return True
        except Exception as e:
            logger.error(f"요청 상태 업데이트 실패: {str(e)}")
            return False

    def create_classification(
        self,
        request_id: Optional[int],
        issue_key: str,
        classified_agent: str,
        confidence: float,
        reasoning: str,
        cached: bool
    ) -> Optional[int]:
        """
        분류 결과 저장

        Args:
            request_id: 요청 ID
            issue_key: 이슈 키
            classified_agent: 선택된 Agent
            confidence: 신뢰도
            reasoning: 분류 이유
            cached: 캐시 사용 여부

        Returns:
            생성된 classification_id 또는 None
        """
        if not self.enabled:
            return None

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO classification_history
                        (request_id, issue_key, classified_agent, confidence, reasoning, cached)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING id
                        """,
                        (request_id, issue_key, classified_agent, confidence, reasoning, cached)
                    )
                    classification_id = cur.fetchone()[0]
                    conn.commit()
                    logger.info(f"분류 이력 생성: {issue_key} → {classified_agent} ({confidence:.2f})")
                    return classification_id
        except Exception as e:
            logger.error(f"분류 이력 생성 실패: {str(e)}")
            return None

    def create_performance_metric(
        self,
        request_id: Optional[int],
        agent_name: str,
        metric_type: str,
        metric_value: float,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        성능 메트릭 저장

        Args:
            request_id: 요청 ID
            agent_name: Agent 이름
            metric_type: 메트릭 유형
            metric_value: 메트릭 값
            metadata: 추가 정보

        Returns:
            성공 여부
        """
        if not self.enabled:
            return False

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO performance_metrics
                        (request_id, agent_name, metric_type, metric_value, metadata)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (request_id, agent_name, metric_type, metric_value, Json(metadata or {}))
                    )
                    conn.commit()
                    logger.debug(f"메트릭 저장: {agent_name}.{metric_type} = {metric_value}")
                    return True
        except Exception as e:
            logger.error(f"메트릭 저장 실패: {str(e)}")
            return False

    def get_request_history(self, issue_key: str) -> List[Dict]:
        """
        이슈 키로 요청 이력 조회

        Args:
            issue_key: Jira 이슈 키

        Returns:
            요청 이력 리스트
        """
        if not self.enabled:
            return []

        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        """
                        SELECT * FROM request_history
                        WHERE issue_key = %s
                        ORDER BY created_at DESC
                        """,
                        (issue_key,)
                    )
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"요청 이력 조회 실패: {str(e)}")
            return []

    def close(self):
        """연결 풀 종료"""
        if self.pool:
            self.pool.closeall()
            logger.info("DB 연결 풀 종료")
```

### SDB Agent DB Manager

**파일**: `sdb-agent/app/db_manager.py` (신규)

```python
"""
PostgreSQL 데이터베이스 매니저 - SDB Agent
"""
import psycopg2
from psycopg2.extras import Json
from psycopg2.pool import ThreadedConnectionPool
from typing import Optional, Dict, List
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseManager:
    """PostgreSQL 데이터베이스 매니저 - SDB Agent용"""

    def __init__(self, host: str, port: int, database: str, user: str, password: str):
        try:
            self.pool = ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                host=host,
                port=port,
                database=database,
                user=user,
                password=password
            )
            logger.info(f"DB 연결 풀 생성 성공: {host}:{port}/{database}")
            self.enabled = True
        except Exception as e:
            logger.error(f"DB 연결 실패: {str(e)}")
            self.enabled = False
            self.pool = None

    @contextmanager
    def get_connection(self):
        """연결 풀에서 연결 가져오기"""
        if not self.enabled:
            yield None
            return

        conn = None
        try:
            conn = self.pool.getconn()
            yield conn
        finally:
            if conn:
                self.pool.putconn(conn)

    def create_code_change(
        self,
        request_id: Optional[int],
        issue_key: str,
        file_path: str,
        change_type: str,
        diff_content: Optional[str] = None,
        branch_name: Optional[str] = None,
        commit_hash: Optional[str] = None,
        pr_url: Optional[str] = None
    ) -> Optional[int]:
        """
        코드 변경 이력 저장

        Args:
            request_id: 요청 ID
            issue_key: 이슈 키
            file_path: 파일 경로
            change_type: 변경 유형 (added, modified, deleted)
            diff_content: Diff 내용
            branch_name: 브랜치 이름
            commit_hash: Commit SHA
            pr_url: PR URL

        Returns:
            생성된 code_change_id 또는 None
        """
        if not self.enabled:
            return None

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO code_change_history
                        (request_id, issue_key, file_path, change_type, diff_content,
                         branch_name, commit_hash, pr_url)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                        """,
                        (request_id, issue_key, file_path, change_type, diff_content,
                         branch_name, commit_hash, pr_url)
                    )
                    code_change_id = cur.fetchone()[0]
                    conn.commit()
                    logger.info(f"코드 변경 이력 생성: {issue_key} - {file_path} ({change_type})")
                    return code_change_id
        except Exception as e:
            logger.error(f"코드 변경 이력 생성 실패: {str(e)}")
            return None

    def create_performance_metric(
        self,
        request_id: Optional[int],
        agent_name: str,
        metric_type: str,
        metric_value: float,
        metadata: Optional[Dict] = None
    ) -> bool:
        """성능 메트릭 저장"""
        if not self.enabled:
            return False

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO performance_metrics
                        (request_id, agent_name, metric_type, metric_value, metadata)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (request_id, agent_name, metric_type, metric_value, Json(metadata or {}))
                    )
                    conn.commit()
                    logger.debug(f"메트릭 저장: {agent_name}.{metric_type} = {metric_value}")
                    return True
        except Exception as e:
            logger.error(f"메트릭 저장 실패: {str(e)}")
            return False
```

---

## Router Agent 통합

**파일**: `router-agent/app/main.py` (수정)

```python
from .db import DatabaseManager
import time

# DB 매니저 초기화
db_manager = DatabaseManager(
    host=settings.db_host,
    port=settings.db_port,
    database=settings.db_name,
    user=settings.db_user,
    password=settings.db_password
)

@app.post("/webhook")
@track_request_metrics("webhook")
async def route_webhook(request: Request):
    start_time = time.time()
    request_id = None

    try:
        payload = await request.json()
        issue = payload.get('issue', {})
        issue_key = issue.get('key', 'UNKNOWN')
        webhook_event = payload.get('webhookEvent')

        logger.info(f"Received webhook for issue: {issue_key}")

        # 1. DB: 요청 이력 생성
        request_id = db_manager.create_request(
            issue_key=issue_key,
            webhook_event=webhook_event,
            payload=payload
        )

        # 2. Intent Classification
        classification = intent_classifier.classify_issue(issue)
        agent_name = classification.get('agent')
        confidence = classification.get('confidence', 0.0)
        reasoning = classification.get('reasoning', '')
        cached = classification.get('cached', False)

        # 3. DB: 분류 결과 저장
        db_manager.create_classification(
            request_id=request_id,
            issue_key=issue_key,
            classified_agent=agent_name,
            confidence=confidence,
            reasoning=reasoning,
            cached=cached
        )

        # 4. Agent 호출
        # ... (기존 코드)

        # 5. DB: 성능 메트릭 저장
        total_duration = time.time() - start_time
        db_manager.create_performance_metric(
            request_id=request_id,
            agent_name='router-agent',
            metric_type='latency',
            metric_value=total_duration,
            metadata={'endpoint': 'webhook'}
        )

        # 6. DB: 요청 상태 업데이트
        db_manager.update_request_status(request_id, 'completed')

        return JSONResponse({
            "status": "success",
            "issue_key": issue_key,
            "request_id": request_id,
            "result": result
        })

    except Exception as e:
        logger.error(f"Routing error: {str(e)}", exc_info=True)

        # DB: 실패 상태 업데이트
        if request_id:
            db_manager.update_request_status(request_id, 'failed')

        raise HTTPException(status_code=500, detail=str(e))
```

**파일**: `router-agent/app/config.py` (추가)

```python
class Settings(BaseSettings):
    # 기존 설정...

    # PostgreSQL 설정
    db_host: str = "postgresql"
    db_port: int = 5432
    db_name: str = "agent_system"
    db_user: str = "agent_user"
    db_password: str
```

**파일**: `router-agent/requirements.txt` (추가)

```txt
psycopg2-binary==2.9.9
```

---

## SDB Agent 통합

**파일**: `sdb-agent/app/main.py` (수정)

```python
from app.db_manager import DatabaseManager
import time
import os

# DB 매니저 초기화
db_manager = DatabaseManager(
    host=os.getenv('DB_HOST', 'postgresql'),
    port=int(os.getenv('DB_PORT', '5432')),
    database=os.getenv('DB_NAME', 'agent_system'),
    user=os.getenv('DB_USER', 'agent_user'),
    password=os.getenv('DB_PASSWORD')
)

@app.route('/process', methods=['POST'])
@custom_metrics.track_processing_time
def process_handler():
    start_time = time.time()
    request_id = None

    try:
        payload = request.get_json()
        issue = payload.get('issue', {})
        metadata = payload.get('metadata', {})

        # Router에서 생성한 request_id 추출 (있으면)
        # 또는 issue_key로 조회
        issue_key = issue.get('key')

        # 이슈 처리
        result = issue_processor.process_issue(issue)

        # 코드 변경 이력 저장
        modified_files = result.get('modified_files', [])
        for file_info in modified_files:
            db_manager.create_code_change(
                request_id=request_id,
                issue_key=issue_key,
                file_path=file_info['path'],
                change_type=file_info.get('change_type', 'modified'),
                diff_content=file_info.get('diff'),
                branch_name=result.get('branch_name'),
                pr_url=result.get('pr_url')
            )

        # 성능 메트릭 저장
        processing_duration = time.time() - start_time
        db_manager.create_performance_metric(
            request_id=request_id,
            agent_name='sdb-agent',
            metric_type='latency',
            metric_value=processing_duration
        )

        # LLM 토큰 사용량 저장 (있으면)
        if 'llm_usage' in result:
            db_manager.create_performance_metric(
                request_id=request_id,
                agent_name='sdb-agent',
                metric_type='llm_tokens',
                metric_value=result['llm_usage']['total_tokens'],
                metadata=result['llm_usage']
            )

        return jsonify({
            'status': 'completed',
            'issue_key': issue_key,
            'result': result
        }), 200

    except Exception as e:
        logger.error(f"처리 중 오류 발생: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'failed',
            'error': str(e)
        }), 500
```

**파일**: `sdb-agent/requirements.txt` (추가)

```txt
psycopg2-binary==2.9.9
```

---

## 백업 및 복구

### 자동 백업 CronJob

**파일**: `helm/multi-agent-system/templates/postgresql/backup-cronjob.yaml`

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgresql-backup
  namespace: {{ .Values.global.namespace }}
spec:
  schedule: "0 2 * * *"  # 매일 새벽 2시
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: backup
              image: postgres:15-alpine
              command:
                - /bin/sh
                - -c
                - |
                  TIMESTAMP=$(date +%Y%m%d_%H%M%S)
                  pg_dump -h postgresql -U $POSTGRES_USER -d $POSTGRES_DB \
                    | gzip > /backup/backup_${TIMESTAMP}.sql.gz
                  echo "Backup completed: backup_${TIMESTAMP}.sql.gz"

                  # 30일 이상 된 백업 삭제
                  find /backup -name "backup_*.sql.gz" -mtime +30 -delete
              env:
                - name: POSTGRES_USER
                  valueFrom:
                    configMapKeyRef:
                      name: postgresql-config
                      key: POSTGRES_USER
                - name: POSTGRES_DB
                  valueFrom:
                    configMapKeyRef:
                      name: postgresql-config
                      key: POSTGRES_DB
                - name: PGPASSWORD
                  valueFrom:
                    secretKeyRef:
                      name: postgresql-secret
                      key: POSTGRES_PASSWORD
              volumeMounts:
                - name: backup
                  mountPath: /backup
          volumes:
            - name: backup
              persistentVolumeClaim:
                claimName: postgresql-backup-pvc
          restartPolicy: OnFailure
```

### 복구 스크립트

```bash
#!/bin/bash
# restore-db.sh

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup-file.sql.gz>"
    exit 1
fi

kubectl exec -it postgresql-0 -n agent-system -- \
    bash -c "gunzip < /backup/$BACKUP_FILE | psql -U agent_user -d agent_system"

echo "Restore completed from $BACKUP_FILE"
```

---

## 성능 최적화

### 1. 연결 풀 크기 조정

```python
# 동시 요청 수에 따라 조정
DatabaseManager(
    min_conn=2,  # 최소 2개 연결 유지
    max_conn=20  # 최대 20개 연결 허용
)
```

### 2. 쿼리 최적화

```sql
-- 느린 쿼리 확인
SELECT
    query,
    calls,
    total_time,
    mean_time,
    max_time
FROM pg_stat_statements
ORDER BY total_time DESC
LIMIT 10;

-- 인덱스 사용 확인
EXPLAIN ANALYZE
SELECT * FROM request_history WHERE issue_key = 'PROJ-123';
```

### 3. VACUUM 및 ANALYZE

```bash
# 주기적 실행 (CronJob)
kubectl exec -it postgresql-0 -n agent-system -- \
    psql -U agent_user -d agent_system -c "VACUUM ANALYZE;"
```

---

## 테스트 및 검증

### 1. DB 연결 테스트

```bash
# PostgreSQL Pod 접속
kubectl exec -it postgresql-0 -n agent-system -- psql -U agent_user -d agent_system

# 테이블 확인
\dt

# 데이터 확인
SELECT COUNT(*) FROM request_history;
```

### 2. 데이터 저장 확인

```bash
# Webhook 전송
curl -X POST http://router-agent/webhook -d @test-webhook.json

# DB에서 확인
kubectl exec -it postgresql-0 -n agent-system -- psql -U agent_user -d agent_system -c \
    "SELECT * FROM request_history ORDER BY created_at DESC LIMIT 1;"
```

### 3. 성능 테스트

```python
# 대량 INSERT 성능 테스트
import time

start = time.time()
for i in range(1000):
    db_manager.create_request(
        issue_key=f'TEST-{i}',
        webhook_event='test',
        payload={'test': i}
    )
duration = time.time() - start
print(f"1000 inserts: {duration:.2f}s ({1000/duration:.0f} req/s)")
```

---

## 검증 체크리스트

- [ ] PostgreSQL이 배포되고 정상 동작함
- [ ] 스키마가 정상적으로 생성됨
- [ ] Router Agent가 DB에 연결됨
- [ ] SDB Agent가 DB에 연결됨
- [ ] Webhook 요청 시 DB에 데이터 저장됨
- [ ] Classification 결과가 DB에 저장됨
- [ ] 코드 변경 이력이 DB에 저장됨
- [ ] 성능 메트릭이 DB에 저장됨
- [ ] 백업 CronJob이 정상 동작함
- [ ] 쿼리 성능이 충분함 (1000건 < 1초)

---

## 트러블슈팅

### 문제 1: DB 연결 실패

**증상**: Agent 로그에 "DB 연결 실패"

**해결**:
```bash
# PostgreSQL Pod 상태 확인
kubectl get pod -n agent-system -l app=postgresql

# Service 확인
kubectl get svc postgresql -n agent-system

# 연결 테스트
kubectl exec -it <agent-pod> -n agent-system -- nc -zv postgresql 5432
```

### 문제 2: 데이터가 저장되지 않음

**증상**: DB 조회 시 데이터 없음

**해결**:
```bash
# Agent 로그 확인
kubectl logs -f <agent-pod> -n agent-system | grep "DB"

# PostgreSQL 로그 확인
kubectl logs -f postgresql-0 -n agent-system
```

### 문제 3: 쿼리 성능 저하

**증상**: 응답 시간 급증

**해결**:
```sql
-- 인덱스 누락 확인
SELECT * FROM pg_stat_user_tables WHERE schemaname = 'public';

-- 테이블 통계 업데이트
ANALYZE;
```

---

## 다음 단계

Phase 3 완료 후:
1. ✅ 1주일 운영하며 데이터 수집
2. ✅ 쿼리 성능 모니터링
3. → [PHASE4_INTEGRATION.md](./PHASE4_INTEGRATION.md) 진행

---

**문서 버전**: 1.0.0
**최종 업데이트**: 2025-10-22
