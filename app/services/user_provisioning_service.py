from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.tenant import Tenant
from app.models.user import User
from app.repositories.tenant_repository import TenantRepository


@dataclass(frozen=True)
class ProvisionedUser:
    user: User
    tenant: Tenant


class UserProvisioningService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._tenants = TenantRepository(db)

    def ensure_user(
        self,
        auth0_user_id: str,
        email: str,
        name: Optional[str],
    ) -> ProvisionedUser:
        """Idempotent upsert of tenant + user. Safe to call on every login."""
        tenant = self._tenants.find_by_auth0_user_id(auth0_user_id)
        if not tenant:
            tenant = Tenant(
                id=str(uuid4()),
                auth0_user_id=auth0_user_id,
                name=name or email,
                plan="free",
                created_at=datetime.utcnow(),
            )
            self._db.add(tenant)
            self._db.flush()

        user = self._db.query(User).filter_by(auth0_user_id=auth0_user_id).first()
        if not user:
            user = User(
                id=str(uuid4()),
                auth0_user_id=auth0_user_id,
                tenant_id=tenant.id,
                email=email,
                name=name,
                role="owner",
                created_at=datetime.utcnow(),
            )
            self._db.add(user)

        self._db.commit()
        self._db.refresh(user)
        return ProvisionedUser(user=user, tenant=tenant)
