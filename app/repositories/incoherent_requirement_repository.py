from datetime import datetime
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
        user_filter: Optional[str] = None,
        since: Optional[datetime] = None,
        skip_tenant_filter: bool = False,
        sort_by: str = "desc",
    ) -> tuple[list[tuple[IncoherentRequirement, Optional[str]]], int]:
        """Return (rows, total) where each row is (record, user_email).

        If skip_tenant_filter=True, returns records from all tenants (super-admin).
        """
        from sqlalchemy import or_
        tid = self._tid() if not skip_tenant_filter else None
        order = IncoherentRequirement.created_at.asc() if sort_by == "asc" else IncoherentRequirement.created_at.desc()

        join_condition = User.id == IncoherentRequirement.user_id
        if not skip_tenant_filter:
            join_condition = join_condition & (User.tenant_id == tid)

        base = self._db.query(IncoherentRequirement)
        if not skip_tenant_filter:
            base = base.filter(IncoherentRequirement.tenant_id == tid)
        base = base.outerjoin(User, join_condition)
        if reason:
            base = base.filter(IncoherentRequirement.reason_codes.like(f'%"{reason}"%'))
        if user_filter:
            base = base.filter(or_(
                User.email.ilike(f"%{user_filter}%"),
                IncoherentRequirement.user_id == user_filter,
            ))
        if since and isinstance(since, datetime):
            base = base.filter(IncoherentRequirement.created_at >= since)

        total = base.with_entities(func.count(IncoherentRequirement.id)).scalar() or 0

        rows = self._db.query(IncoherentRequirement, User.email)
        if not skip_tenant_filter:
            rows = rows.filter(IncoherentRequirement.tenant_id == tid)
        rows = rows.outerjoin(User, join_condition)
        if reason:
            rows = rows.filter(IncoherentRequirement.reason_codes.like(f'%"{reason}"%'))
        if user_filter:
            rows = rows.filter(or_(
                User.email.ilike(f"%{user_filter}%"),
                IncoherentRequirement.user_id == user_filter,
            ))
        if since and isinstance(since, datetime):
            rows = rows.filter(IncoherentRequirement.created_at >= since)

        rows = rows.order_by(order).offset(offset).limit(limit).all()
        return [(rec, email) for rec, email in rows], int(total)
