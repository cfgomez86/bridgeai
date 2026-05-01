from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class RequirementUnderstanding:
    requirement_id: str
    requirement_text: str
    project_id: str
    intent: str
    action: str
    entity: str
    feature_type: str
    priority: str
    business_domain: str
    technical_scope: str
    estimated_complexity: str
    keywords: list[str]
    created_at: datetime
    processing_time_seconds: float
    coherence_model: str | None = None
    coherence_calls: int = 0
    parser_model: str | None = None
    parser_calls: int = 0
