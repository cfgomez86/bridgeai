from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    DATABASE_URL: str = "sqlite:///./app.db"

    # Project
    PROJECT_ROOT: str = "."
    LOG_LEVEL: str = "INFO"

    # Feature flags
    DRY_RUN: bool = False

    @property
    def project_root_path(self) -> Path:
        return Path(self.PROJECT_ROOT).resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
