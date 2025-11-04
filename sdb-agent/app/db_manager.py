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
        """
        Args:
            host: DB 호스트
            port: DB 포트
            database: 데이터베이스 이름
            user: 사용자
            password: 비밀번호
        """
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

    def close(self):
        """연결 풀 종료"""
        if self.pool:
            self.pool.closeall()
            logger.info("DB 연결 풀 종료")
