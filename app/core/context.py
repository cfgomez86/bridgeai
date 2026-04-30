from contextvars import ContextVar
from typing import Optional

current_tenant_id: ContextVar[Optional[str]] = ContextVar("current_tenant_id", default=None)
current_user_id: ContextVar[Optional[str]] = ContextVar("current_user_id", default=None)


def get_tenant_id() -> str:
    tid = current_tenant_id.get()
    if not tid:
        raise RuntimeError(
            "Tenant context not set. "
            "Authenticated routes must use Depends(get_current_user). "
            "Unauthenticated callbacks (e.g. OAuth) must call current_tenant_id.set() "
            "explicitly from a trusted source such as a stored OAuth state record."
        )
    return tid


def get_user_id() -> str:
    uid = current_user_id.get()
    if not uid:
        raise RuntimeError(
            "User context not set. "
            "Authenticated routes must use Depends(get_current_user)."
        )
    return uid
