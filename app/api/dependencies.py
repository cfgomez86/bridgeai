from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.auth0_auth import verify_auth0_jwt, _extract_bearer_token
from app.core.context import current_tenant_id, current_user_id
from app.database.session import get_db
from app.models.user import User


async def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    token = _extract_bearer_token(request)
    payload = verify_auth0_jwt(token)

    auth0_user_id = payload.get("sub")
    if not auth0_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims")

    user = db.query(User).filter_by(auth0_user_id=auth0_user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not provisioned. Call POST /api/v1/auth/provision first.",
        )

    current_tenant_id.set(user.tenant_id)
    current_user_id.set(user.id)
    return user
