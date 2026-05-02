import json
from typing import TYPE_CHECKING, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.api.dependencies import get_current_user, get_incoherent_requirement_repo
from app.core.logging import get_logger
from app.models.user import User
from app.services.requirement_coherence_validator import VALID_REASON_CODES

if TYPE_CHECKING:
    from app.repositories.incoherent_requirement_repository import IncoherentRequirementRepository

_REQUIREMENT_TEXT_PREVIEW_LEN = 200

logger = get_logger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)], tags=["admin"])


class IncoherentRequirementItem(BaseModel):
    id: str
    requirement_text_preview: str  # first 200 chars; full text available via detail endpoint
    warning: Optional[str] = None
    reason_codes: list[str]
    user_id: str
    user_email: Optional[str] = None
    project_id: Optional[str] = None
    source_connection_id: Optional[str] = None
    model_used: Optional[str] = None
    created_at: str


class IncoherentRequirementListResponse(BaseModel):
    items: list[IncoherentRequirementItem]
    total: int
    limit: int
    offset: int


@router.get(
    "/admin/incoherent-requirements",
    response_model=IncoherentRequirementListResponse,
)
async def list_incoherent_requirements(
    reason: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    repo: "IncoherentRequirementRepository" = Depends(get_incoherent_requirement_repo),
    user: User = Depends(get_current_user),
) -> IncoherentRequirementListResponse:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required to view incoherent requirements",
        )
    if reason is not None and reason not in VALID_REASON_CODES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"reason must be one of: {', '.join(sorted(VALID_REASON_CODES))}",
        )

    rows, total = repo.list_with_user(limit=limit, offset=offset, reason=reason)

    items: list[IncoherentRequirementItem] = []
    for record, email in rows:
        try:
            codes = json.loads(record.reason_codes)
            if not isinstance(codes, list):
                codes = []
        except (json.JSONDecodeError, TypeError):
            codes = []
        preview = record.requirement_text[:_REQUIREMENT_TEXT_PREVIEW_LEN]
        items.append(
            IncoherentRequirementItem(
                id=record.id,
                requirement_text_preview=preview,
                warning=record.warning,
                reason_codes=[str(c) for c in codes],
                user_id=record.user_id,
                user_email=email,
                project_id=record.project_id,
                source_connection_id=record.source_connection_id,
                model_used=record.model_used,
                created_at=record.created_at.isoformat() if record.created_at else "",
            )
        )

    return IncoherentRequirementListResponse(
        items=items, total=total, limit=limit, offset=offset
    )
