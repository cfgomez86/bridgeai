import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# APP_ENV selects the environment overlay file:
#   local   → .env + .env.local   (default)
#   prod    → .env + .env.prod
_APP_ENV = os.getenv("APP_ENV", "local")


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

    # Indexing
    INDEXING_MAX_WORKERS: int = 20

    # AI Provider
    AI_PROVIDER: str = "stub"
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    AI_MODEL: str = ""
    AI_TIMEOUT_SECONDS: int = 60
    AI_MAX_RETRIES: int = 2
    AI_MAX_OUTPUT_TOKENS: int = 8192

    # Story entity existence validation
    ENTITY_VALIDATION_MODE: str = "warn"  # "warn" | "off"

    # Jira integration
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
    # Regex pattern for additional allowed CORS origins. Empty = disabled.
    # Example: https://.*\.devtunnels\.ms — matches any VS Code devtunnel URL.
    # Override with an empty string in production to disable.
    CORS_ORIGIN_REGEX: str = ""

    # IPs allowed to set X-Forwarded-* headers (Next.js rewrite proxy, nginx, etc.)
    # Restrict to loopback in all environments; extend only if your proxy runs on a
    # different host.
    TRUSTED_PROXY_IPS: str = "127.0.0.1,::1"

    # Field-level encryption for sensitive DB columns (OAuth tokens, PATs)
    # Generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    # Required for DORA compliance. Tokens are stored unencrypted with a warning when absent.
    FIELD_ENCRYPTION_KEY: str = ""

    # Auth0
    AUTH0_DOMAIN: str = ""      # e.g. "my-tenant.eu.auth0.com"
    AUTH0_AUDIENCE: str = ""    # e.g. "https://api.bridgeai.com"

    # First-party OAuth credentials — overridden per environment
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GITLAB_CLIENT_ID: str = ""
    GITLAB_CLIENT_SECRET: str = ""
    AZURE_DEVOPS_CLIENT_ID: str = ""
    AZURE_DEVOPS_CLIENT_SECRET: str = ""
    BITBUCKET_CLIENT_ID: str = ""
    BITBUCKET_CLIENT_SECRET: str = ""
    JIRA_CLIENT_ID: str = ""
    JIRA_CLIENT_SECRET: str = ""

    # Quality Judge (LLM-as-Judge)
    AI_JUDGE_PROVIDER: str = ""   # if empty, uses AI_PROVIDER
    AI_JUDGE_MODEL: str = ""      # if empty, uses AI_MODEL
    AI_JUDGE_ENABLED: bool = True
    AI_JUDGE_SAMPLES: int = 3
    AI_JUDGE_TEMPERATURE: float = 0.3
    EVAL_REPORT_PATH: str = "./eval_report.json"

    @property
    def project_root_path(self) -> Path:
        return Path(self.PROJECT_ROOT).resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
