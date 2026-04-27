from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Repository:
    full_name: str
    name: str
    owner: str
    default_branch: str
    private: bool


@dataclass(frozen=True)
class SourceConnection:
    id: str
    platform: str
    display_name: str
    repo_full_name: str | None
    repo_name: str | None
    owner: str | None
    default_branch: str
    is_active: bool
    created_at: datetime
    boards_project: str | None = None
    auth_method: str = "oauth"
