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
    subtasks: dict  # {"frontend": [...], "backend": [...], "configuration": [...]}
    definition_of_done: list[str]
    risk_notes: list[str]
    story_points: int
    risk_level: str
    created_at: datetime
    generation_time_seconds: float
