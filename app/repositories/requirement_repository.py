from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.core.context import get_tenant_id
from app.models.requirement import Requirement


class RequirementRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def _tid(self) -> str:
        return get_tenant_id()

    def save(self, data: dict, source_connection_id: str) -> Requirement:
        req = Requirement(
            **data,
            tenant_id=self._tid(),
            source_connection_id=source_connection_id,
        )
        self._db.add(req)
        self._db.commit()
        self._db.refresh(req)
        return req

    def find_by_id(self, requirement_id: str, source_connection_id: str) -> Optional[Requirement]:
        return (
            self._db.query(Requirement)
            .filter(
                Requirement.id == requirement_id,
                Requirement.tenant_id == self._tid(),
                Requirement.source_connection_id == source_connection_id,
            )
            .first()
        )

    def find_by_text_project_and_connection(
        self, text_hash: str, project_id: str, source_connection_id: str
    ) -> Optional[Requirement]:
        return (
            self._db.query(Requirement)
            .filter(
                Requirement.tenant_id == self._tid(),
                Requirement.source_connection_id == source_connection_id,
                Requirement.requirement_text_hash == text_hash,
                Requirement.project_id == project_id,
            )
            .first()
        )

    def count_since(self, since: Optional[datetime]) -> int:
        q = self._db.query(Requirement).filter(Requirement.tenant_id == self._tid())
        if since is not None:
            q = q.filter(Requirement.created_at >= since)
        return q.count()

    def list_by_project(
        self, project_id: str, source_connection_id: str
    ) -> list[Requirement]:
        return (
            self._db.query(Requirement)
            .filter(
                Requirement.tenant_id == self._tid(),
                Requirement.source_connection_id == source_connection_id,
                Requirement.project_id == project_id,
            )
            .all()
        )
