import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# APP_ENV selects the environment overlay file:
#   local   → .env + .env.local   (default)
#   tunnel  → .env + .env.tunnel
#   prod    → .env + .env.prod
_APP_ENV = os.getenv("APP_ENV", "tunnel")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Files listed last take precedence — overlay overrides base.
        env_file=[".env", f".env.{_APP_ENV}"],
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/bridgeai"

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
    JIRA_ISSUE_TYPE_MAP: str = ""

    # Azure DevOps integration
    AZURE_DEVOPS_TOKEN: str = ""
    AZURE_ORG_URL: str = ""
    AZURE_PROJECT: str = ""
    AZURE_REQUEST_TIMEOUT_SECONDS: int = 10
    AZURE_MAX_RETRIES: int = 3
    AZURE_RETRY_DELAY_SECONDS: int = 5

    # URLs — overridden per environment in .env.{APP_ENV}
    FRONTEND_URL: str = "http://localhost:3000"
    API_BASE_URL: str = "http://localhost:8000"
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # IPs allowed to set X-Forwarded-* headers (Next.js rewrite proxy, nginx, etc.)
    # Restrict to loopback in all environments; extend only if your proxy runs on a
    # different host.
    TRUSTED_PROXY_IPS: str = "127.0.0.1,::1"

    # Clerk auth
    CLERK_SECRET_KEY: str = ""

    # First-party OAuth credentials — overridden per environment
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GITLAB_CLIENT_ID: str = ""
    GITLAB_CLIENT_SECRET: str = ""
    AZURE_DEVOPS_CLIENT_ID: str = ""
    AZURE_DEVOPS_CLIENT_SECRET: str = ""

    @property
    def project_root_path(self) -> Path:
        return Path(self.PROJECT_ROOT).resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
