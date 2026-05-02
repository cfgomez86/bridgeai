from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.context import get_tenant_id
from app.models.incoherent_requirement import IncoherentRequirement
from app.models.user import User


class IncoherentRequirementRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def _tid(self) -> str:
        return get_tenant_id()

    def save(self, record: dict) -> IncoherentRequirement:
        row = IncoherentRequirement(
            id=record["id"],
            tenant_id=self._tid(),
            user_id=record["user_id"],
            requirement_text=record["requirement_text"],
            requirement_text_hash=record["requirement_text_hash"],
            warning=record.get("warning"),
            reason_codes=record["reason_codes"],
            project_id=record.get("project_id"),
            source_connection_id=record.get("source_connection_id"),
            model_used=record.get("model_used"),
        )
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row

    def list_with_user(
        self,
        limit: int,
        offset: int,
        reason: Optional[str] = None,
    ) -> tuple[list[tuple[IncoherentRequirement, Optional[str]]], int]:
        """Return (rows, total) where each row is (record, user_email).

        `reason` filters by membership in the JSON-serialized `reason_codes` list.
        """
        tid = self._tid()
        base = self._db.query(IncoherentRequirement).filter(
            IncoherentRequirement.tenant_id == tid
        )
        if reason:
            base = base.filter(IncoherentRequirement.reason_codes.like(f'%"{reason}"%'))

        total = base.with_entities(func.count(IncoherentRequirement.id)).scalar() or 0

        rows = (
            self._db.query(IncoherentRequirement, User.email)
            .filter(IncoherentRequirement.tenant_id == tid)
            .outerjoin(
                User,
                (User.id == IncoherentRequirement.user_id)
                & (User.tenant_id == tid),
            )
        )
        if reason:
            rows = rows.filter(IncoherentRequirement.reason_codes.like(f'%"{reason}"%'))
        rows = (
            rows.order_by(IncoherentRequirement.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [(rec, email) for rec, email in rows], int(total)
