from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class TicketResult:
    external_id: str
    url: str
    provider: str
    status: str  # CREATED | FAILED | DUPLICATE


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
