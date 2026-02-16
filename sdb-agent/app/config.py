"""
SDB Agent 설정 관리
"""

import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """SDB Agent 설정"""

    # Bitbucket 설정
    bitbucket_url: str = "https://api.bitbucket.org"
    bitbucket_username: str = "api_user"
    bitbucket_access_token: Optional[str] = None
    bitbucket_repository: str = "genw_new"
    bitbucket_workspace: str = "mit_dev"

    # OpenAI 설정
    openai_api_key: str = ""
    openai_model: str = "gpt-4-turbo-preview"

    # 로깅 설정
    log_level: str = "INFO"

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

    # 테스트 모드 설정
    test_mode: bool = False
    flask_env: str = "production"

    # Flask 포트 설정
    port: int = 5000

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # .env의 추가 필드 무시


def get_settings() -> Settings:
    """설정 인스턴스 반환"""
    return Settings()
