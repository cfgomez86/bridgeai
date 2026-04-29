import json
from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.context import get_tenant_id
from app.domain.user_story import UserStory as DomainUserStory
from app.models.user_story import UserStory
from app.utils.json_utils import parse_json_field

_JSON_FIELDS = frozenset({"acceptance_criteria", "subtasks", "definition_of_done", "risk_notes"})


class UserStoryRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def _tid(self) -> str:
        return get_tenant_id()

    def save(self, story: UserStory, source_connection_id: str) -> UserStory:
        story.tenant_id = self._tid()
        story.source_connection_id = source_connection_id
        self._db.add(story)
        self._db.commit()
        self._db.refresh(story)
        return story

    def find_by_id(self, story_id: str) -> Optional[UserStory]:
        """Devuelve la historia si pertenece al tenant actual. Sin filtro de conexión
        porque el caller normalmente no conoce aún la conexión — se expone en la
        respuesta para que el frontend valide."""
        return (
            self._db.query(UserStory)
            .filter(UserStory.id == story_id, UserStory.tenant_id == self._tid())
            .first()
        )

    def find_by_id_scoped(
        self, story_id: str, source_connection_id: str
    ) -> Optional[UserStory]:
        """Variante estricta que además valida la conexión. Usar cuando el caller
        ya tiene el source_connection_id del contexto."""
        return (
            self._db.query(UserStory)
            .filter(
                UserStory.id == story_id,
                UserStory.tenant_id == self._tid(),
                UserStory.source_connection_id == source_connection_id,
            )
            .first()
        )

    @staticmethod
    def to_domain(model: "UserStory") -> DomainUserStory:
        """Convert an ORM UserStory to a DomainUserStory without an extra DB query."""
        return DomainUserStory(
            story_id=model.id,
            requirement_id=model.requirement_id,
            impact_analysis_id=model.impact_analysis_id,
            project_id=model.project_id,
            title=model.title,
            story_description=model.story_description,
            acceptance_criteria=parse_json_field(model.acceptance_criteria),
            subtasks=json.loads(model.subtasks) if model.subtasks else {"frontend": [], "backend": [], "configuration": []},
            definition_of_done=parse_json_field(model.definition_of_done),
            risk_notes=parse_json_field(model.risk_notes),
            story_points=model.story_points,
            risk_level=model.risk_level,
            created_at=model.created_at,
            generation_time_seconds=model.generation_time_seconds,
        )

    def find_domain_by_id(self, story_id: str) -> Optional[DomainUserStory]:
        model = self.find_by_id(story_id)
        if not model:
            return None
        return self.to_domain(model)

    def update_story(
        self,
        story_id: str,
        source_connection_id: str,
        **fields,
    ) -> Optional[UserStory]:
        """Update editable fields of a story. JSON list/dict fields are re-serialised."""
        story = self.find_by_id_scoped(story_id, source_connection_id)
        if story is None:
            return None
        for key, value in fields.items():
            if key in _JSON_FIELDS and not isinstance(value, str):
                value = json.dumps(value, ensure_ascii=False)
            setattr(story, key, value)
        self._db.commit()
        self._db.refresh(story)
        return story

    def count_since(self, since: Optional[datetime]) -> int:
        q = self._db.query(UserStory).filter(UserStory.tenant_id == self._tid())
        if since is not None:
            q = q.filter(UserStory.created_at >= since)
        return q.count()

    def list_recent(self, limit: int) -> list[UserStory]:
        return (
            self._db.query(UserStory)
            .filter(UserStory.tenant_id == self._tid())
            .order_by(UserStory.created_at.desc())
            .limit(limit)
            .all()
        )

    def count_by_risk_since(self, since: Optional[datetime]) -> dict[str, int]:
        q = (
            self._db.query(UserStory.risk_level, func.count(UserStory.id))
            .filter(UserStory.tenant_id == self._tid())
        )
        if since is not None:
            q = q.filter(UserStory.created_at >= since)
        rows = q.group_by(UserStory.risk_level).all()
        counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
        for risk, count in rows:
            key = (risk or "").upper()
            if key in counts:
                counts[key] = count
        return counts

    def find_by_requirement_and_analysis(
        self,
        requirement_id: str,
        analysis_id: str,
        source_connection_id: str,
        language: str = "es",
    ) -> Optional[UserStory]:
        return (
            self._db.query(UserStory)
            .filter(
                UserStory.tenant_id == self._tid(),
                UserStory.source_connection_id == source_connection_id,
                UserStory.requirement_id == requirement_id,
                UserStory.impact_analysis_id == analysis_id,
                UserStory.language == language,
            )
            .first()
        )
