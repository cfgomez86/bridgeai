import json
from typing import Optional

from sqlalchemy.orm import Session

from app.core.context import get_tenant_id
from app.domain.user_story import UserStory as DomainUserStory
from app.models.user_story import UserStory
from app.utils.json_utils import parse_json_field


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

    def find_domain_by_id(self, story_id: str) -> Optional[DomainUserStory]:
        model = self.find_by_id(story_id)
        if not model:
            return None
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
