from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class TicketResult:
    external_id: str
    url: str
    provider: str
    status: str  # CREATED | FAILED | DUPLICATE
    subtask_ids: list[str] = field(default_factory=list)
    subtask_urls: list[str] = field(default_factory=list)
    subtask_titles: list[str] = field(default_factory=list)
    failed_subtasks: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TicketIntegration:
    id: str
    story_id: str
    provider: str
    project_key: str
    issue_type: str
    external_ticket_id: str | None
    status: str  # PENDING | CREATED | FAILED | RETRYING
    retry_count: int
    error_message: str | None
    created_at: datetime
    updated_at: datetime
