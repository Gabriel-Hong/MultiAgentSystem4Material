"""
Router Agent 설정 관리
"""

import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Router Agent 설정"""
    
    # OpenAI 설정
    openai_api_key: str = ""
    openai_model: str = "gpt-4-turbo-preview"
    
    # 라우팅 설정
    router_timeout: int = 300
    classification_confidence_threshold: float = 0.5
    
    # 로깅 설정
    log_level: str = "INFO"
    
    # Agent Registry 설정
    sdb_agent_url: str = "http://sdb-agent-svc:5000"

    # Redis 설정 (Kubernetes: 환경 변수로 주입, 로컬: .env 또는 기본값)
    redis_host: str = "localhost"  # 로컬 개발 환경 기본값
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None

    # PostgreSQL 설정 (Kubernetes: 환경 변수로 주입, 로컬: .env 또는 기본값)
    db_host: str = "postgresql"
    db_port: int = 5432
    db_name: str = "agent_system"
    db_user: str = "agent_user"
    db_password: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # .env의 추가 필드 무시 (BITBUCKET, JIRA 등)


def get_settings() -> Settings:
    """설정 인스턴스 반환"""
    return Settings()

