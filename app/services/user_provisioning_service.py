from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.repositories.tenant_repository import TenantRepository
from app.repositories.user_repository import UserRepository


@dataclass(frozen=True)
class ProvisionedUser:
    user_id: str
    tenant_id: str
    email: str
    name: Optional[str]
    role: str
    tenant_name: str


class UserProvisioningService:
    def __init__(self, db: Session) -> None:
        self._tenant_repo = TenantRepository(db)
        self._user_repo = UserRepository(db)
        self._db = db

    def ensure_user(
        self,
        auth0_user_id: str,
        email: str,
        name: Optional[str],
    ) -> ProvisionedUser:
        """Idempotent upsert of tenant + user. Safe to call on every login."""
        tenant = self._tenant_repo.find_by_auth0_user_id(auth0_user_id)
        if not tenant:
            tenant = self._tenant_repo.create(
                auth0_user_id=auth0_user_id,
                name=name or email,
            )
            self._db.flush()

        user = self._user_repo.find_by_auth0_user_id(auth0_user_id)
        if not user:
            user = self._user_repo.create(
                auth0_user_id=auth0_user_id,
                tenant_id=tenant.id,
                email=email,
                name=name,
            )

        self._db.commit()
        self._db.refresh(user)
        return ProvisionedUser(
            user_id=user.id,
            tenant_id=tenant.id,
            email=user.email,
            name=user.name,
            role=user.role,
            tenant_name=tenant.name,
        )
