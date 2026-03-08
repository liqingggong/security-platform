from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("config/.env", "config/.env.example", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    PROJECT_NAME: str = "Security Platform"
    DEBUG: bool = False
    # 注意：SECRET_KEY 必须在生产环境中设置
    # 使用以下命令生成：python -c "import secrets; print(secrets.token_urlsafe(32))"
    SECRET_KEY: str = "INSECURE_DEFAULT_KEY_CHANGE_ME_IN_PRODUCTION"
    
    # Base directory for the project
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent

    # Database
    POSTGRES_USER: str = "user"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "security_platform"

    # Redis / Celery
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # Platform-managed FOFA credential (initial/default; can be overridden in DB later)
    FOFA_EMAIL: Optional[str] = None
    FOFA_KEY: Optional[str] = None

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def celery_broker_url(self) -> str:
        return self.redis_url

    @property
    def celery_result_backend(self) -> str:
        return self.redis_url


@lru_cache
def get_settings() -> Settings:
    return Settings()


# 导出 settings 实例，方便直接导入使用
settings = get_settings()
