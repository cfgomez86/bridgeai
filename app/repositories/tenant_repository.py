from typing import Optional

from sqlalchemy.orm import Session

from app.models.tenant import Tenant


class TenantRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_auth0_user_id(self, auth0_user_id: str) -> Optional[Tenant]:
        return self._db.query(Tenant).filter_by(auth0_user_id=auth0_user_id).first()

    def find_by_id(self, tenant_id: str) -> Optional[Tenant]:
        return self._db.query(Tenant).filter_by(id=tenant_id).first()
