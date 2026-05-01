from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class UserStory:
    story_id: str
    requirement_id: str
    impact_analysis_id: str
    project_id: str
    title: str
    story_description: str
    acceptance_criteria: list[str]
    subtasks: dict  # {"frontend": [{"title": str, "description": str}], "backend": [...], "configuration": [...]}
    definition_of_done: list[str]
    risk_notes: list[str]
    story_points: int
    risk_level: str
    created_at: datetime
    generation_time_seconds: float
    entity_not_found: bool = False
    was_forced: bool = False
    force_reason: str | None = None
    generator_model: str | None = None
    generator_calls: int = 0
