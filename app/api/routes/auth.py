from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth0_auth import get_current_user, verify_auth0_jwt, _extract_bearer_token
from app.database.session import get_db
from app.models.user import User
from app.repositories.tenant_repository import TenantRepository
from app.services.user_provisioning_service import UserProvisioningService

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class ProvisionRequest(BaseModel):
    user_email: str
    user_name: str | None = None


class UserResponse(BaseModel):
    user_id: str
    email: str
    name: str | None
    role: str
    tenant_id: str
    tenant_name: str


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/provision", response_model=UserResponse, status_code=status.HTTP_200_OK)
def provision(
    request: Request,
    body: ProvisionRequest,
    db: Session = Depends(get_db),
):
    """Idempotent: creates personal workspace on first login, returns existing on subsequent calls."""
    token = _extract_bearer_token(request)
    payload = verify_auth0_jwt(token)

    auth0_user_id = payload.get("sub")
    if not auth0_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims")

    provisioned = UserProvisioningService(db).ensure_user(
        auth0_user_id=auth0_user_id,
        email=body.user_email,
        name=body.user_name,
    )
    user, tenant = provisioned.user, provisioned.tenant
    return UserResponse(
        user_id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        tenant_id=user.tenant_id,
        tenant_name=tenant.name,
    )


@router.get("/me", response_model=UserResponse)
def me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tenant = TenantRepository(db).find_by_id(current_user.tenant_id)
    return UserResponse(
        user_id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        role=current_user.role,
        tenant_id=current_user.tenant_id,
        tenant_name=tenant.name if tenant else "",
    )
