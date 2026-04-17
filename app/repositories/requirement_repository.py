from typing import Optional
from sqlalchemy.orm import Session
from app.models.requirement import Requirement


class RequirementRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def save(self, req: Requirement) -> Requirement:
        self._db.add(req)
        self._db.commit()
        self._db.refresh(req)
        return req

    def find_by_id(self, requirement_id: str) -> Optional[Requirement]:
        return self._db.get(Requirement, requirement_id)

    def find_by_text_and_project(self, text_hash: str, project_id: str) -> Optional[Requirement]:
        return (
            self._db.query(Requirement)
            .filter(Requirement.requirement_text_hash == text_hash, Requirement.project_id == project_id)
            .first()
        )

    def list_by_project(self, project_id: str) -> list[Requirement]:
        return self._db.query(Requirement).filter(Requirement.project_id == project_id).all()
