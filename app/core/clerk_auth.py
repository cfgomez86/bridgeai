from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from clerk_backend_api.security.verifytoken import verify_token
from clerk_backend_api.security.types import VerifyTokenOptions

from app.core.config import get_settings
from app.core.context import current_tenant_id, current_user_id
from app.database.session import get_db
from app.models.user import User


def _extract_bearer_token(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )
    return auth.removeprefix("Bearer ")


def verify_clerk_jwt(token: str) -> dict:
    settings = get_settings()
    try:
        return verify_token(token, VerifyTokenOptions(secret_key=settings.CLERK_SECRET_KEY))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {exc}",
        )


async def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    token = _extract_bearer_token(request)
    payload = verify_clerk_jwt(token)

    clerk_user_id = payload.get("sub")
    if not clerk_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims")

    user = db.query(User).filter_by(clerk_user_id=clerk_user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not provisioned. Call POST /api/v1/auth/provision first.",
        )

    current_tenant_id.set(user.tenant_id)
    current_user_id.set(user.id)
    return user
