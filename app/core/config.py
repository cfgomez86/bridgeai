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

    # AI Provider
    AI_PROVIDER: str = "stub"
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    AI_MODEL: str = ""
    AI_TIMEOUT_SECONDS: int = 30
    AI_MAX_RETRIES: int = 2

    # Jira integration
    JIRA_BASE_URL: str = ""
    JIRA_USER_EMAIL: str = ""
    JIRA_API_TOKEN: str = ""
    JIRA_REQUEST_TIMEOUT_SECONDS: int = 10
    JIRA_MAX_RETRIES: int = 3
    JIRA_RETRY_DELAY_SECONDS: int = 5
    # Override issue type names when your Jira project uses a different language.
    # Format: "Story=Historia,Task=Tarea,Bug=Error"
    JIRA_ISSUE_TYPE_MAP: str = ""

    # Azure DevOps integration
    AZURE_DEVOPS_TOKEN: str = ""
    AZURE_ORG_URL: str = ""       # https://dev.azure.com/your-org
    AZURE_PROJECT: str = ""
    AZURE_REQUEST_TIMEOUT_SECONDS: int = 10
    AZURE_MAX_RETRIES: int = 3
    AZURE_RETRY_DELAY_SECONDS: int = 5

    @property
    def project_root_path(self) -> Path:
        return Path(self.PROJECT_ROOT).resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
