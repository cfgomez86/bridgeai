from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.clerk_auth import get_current_user, verify_clerk_jwt, _extract_bearer_token
from app.database.session import get_db
from app.models.tenant import Tenant
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class ProvisionRequest(BaseModel):
    tenant_name: str
    tenant_slug: str
    clerk_org_id: str
    user_email: str
    user_name: str | None = None


class UserResponse(BaseModel):
    user_id: str
    clerk_user_id: str
    email: str
    name: str | None
    role: str
    tenant_id: str
    tenant_slug: str
    tenant_name: str


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/provision", response_model=UserResponse, status_code=status.HTTP_200_OK)
def provision(
    request: Request,
    body: ProvisionRequest,
    db: Session = Depends(get_db),
):
    """Idempotent: creates tenant + user on first login, returns existing on subsequent calls."""
    token = _extract_bearer_token(request)
    payload = verify_clerk_jwt(token)

    clerk_user_id = payload.get("sub")
    if not clerk_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims")

    org_role = payload.get("org_role", "org:member")
    role = org_role.removeprefix("org:")

    # Upsert tenant
    tenant = db.query(Tenant).filter_by(clerk_org_id=body.clerk_org_id).first()
    if not tenant:
        tenant = Tenant(
            id=str(uuid4()),
            clerk_org_id=body.clerk_org_id,
            slug=body.tenant_slug,
            name=body.tenant_name,
            plan="free",
            created_at=datetime.utcnow(),
        )
        db.add(tenant)
        db.flush()

    # Upsert user
    user = db.query(User).filter_by(clerk_user_id=clerk_user_id).first()
    if not user:
        user = User(
            id=str(uuid4()),
            clerk_user_id=clerk_user_id,
            tenant_id=tenant.id,
            email=body.user_email,
            name=body.user_name,
            role=role,
            created_at=datetime.utcnow(),
        )
        db.add(user)

    db.commit()
    db.refresh(user)

    return UserResponse(
        user_id=user.id,
        clerk_user_id=user.clerk_user_id,
        email=user.email,
        name=user.name,
        role=user.role,
        tenant_id=user.tenant_id,
        tenant_slug=tenant.slug,
        tenant_name=tenant.name,
    )


@router.get("/me", response_model=UserResponse)
def me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tenant = db.query(Tenant).filter_by(id=current_user.tenant_id).first()
    return UserResponse(
        user_id=current_user.id,
        clerk_user_id=current_user.clerk_user_id,
        email=current_user.email,
        name=current_user.name,
        role=current_user.role,
        tenant_id=current_user.tenant_id,
        tenant_slug=tenant.slug if tenant else "",
        tenant_name=tenant.name if tenant else "",
    )
