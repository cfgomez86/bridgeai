from typing import Optional

from sqlalchemy.orm import Session

from app.core.context import current_tenant_id, get_tenant_id
from app.models.requirement import Requirement


class RequirementRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def _tid(self) -> str:
        return get_tenant_id()

    def save(self, req: Requirement) -> Requirement:
        req.tenant_id = self._tid()
        self._db.add(req)
        self._db.commit()
        self._db.refresh(req)
        return req

    def find_by_id(self, requirement_id: str) -> Optional[Requirement]:
        return (
            self._db.query(Requirement)
            .filter(Requirement.id == requirement_id, Requirement.tenant_id == self._tid())
            .first()
        )

    def find_by_text_and_project(self, text_hash: str, project_id: str) -> Optional[Requirement]:
        return (
            self._db.query(Requirement)
            .filter(
                Requirement.tenant_id == self._tid(),
                Requirement.requirement_text_hash == text_hash,
                Requirement.project_id == project_id,
            )
            .first()
        )

    def list_by_project(self, project_id: str) -> list[Requirement]:
        return (
            self._db.query(Requirement)
            .filter(Requirement.tenant_id == self._tid(), Requirement.project_id == project_id)
            .all()
        )
