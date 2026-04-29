from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_auth0_user_id(self, auth0_user_id: str) -> Optional[User]:
        return self._db.query(User).filter_by(auth0_user_id=auth0_user_id).first()

    def create(
        self,
        auth0_user_id: str,
        tenant_id: str,
        email: str,
        name: Optional[str],
        role: str = "owner",
    ) -> User:
        user = User(
            id=str(uuid4()),
            auth0_user_id=auth0_user_id,
            tenant_id=tenant_id,
            email=email,
            name=name,
            role=role,
            created_at=datetime.utcnow(),
        )
        self._db.add(user)
        return user
