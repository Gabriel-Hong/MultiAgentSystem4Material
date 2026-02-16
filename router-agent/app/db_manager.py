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
        if not self.enabled or request_id is None:
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
