"""Unit tests for UserProvisioningService (A-10) and TenantRepository (A-11)."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.session import Base
from app.repositories.tenant_repository import TenantRepository
from app.services.user_provisioning_service import UserProvisioningService


def make_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


# ---------------------------------------------------------------------------
# TenantRepository
# ---------------------------------------------------------------------------

def test_tenant_repo_find_by_id_returns_none_when_missing():
    db = make_db()
    assert TenantRepository(db).find_by_id("nonexistent") is None


def test_tenant_repo_find_by_auth0_user_id_returns_none_when_missing():
    db = make_db()
    assert TenantRepository(db).find_by_auth0_user_id("auth0|unknown") is None


# ---------------------------------------------------------------------------
# UserProvisioningService
# ---------------------------------------------------------------------------

def test_ensure_user_creates_tenant_and_user_on_first_call():
    db = make_db()
    result = UserProvisioningService(db).ensure_user(
        auth0_user_id="auth0|user-1",
        email="user@example.com",
        name="Test User",
    )
    assert result.email == "user@example.com"
    assert result.role == "owner"
    assert result.tenant_name == "Test User"
    assert result.tenant_id is not None


def test_ensure_user_is_idempotent():
    """Calling ensure_user twice must not duplicate tenant or user."""
    db = make_db()
    svc = UserProvisioningService(db)
    first = svc.ensure_user("auth0|user-2", "user2@example.com", "User Two")
    second = svc.ensure_user("auth0|user-2", "user2@example.com", "User Two")

    assert first.user_id == second.user_id
    assert first.tenant_id == second.tenant_id


def test_ensure_user_falls_back_to_email_when_name_is_none():
    db = make_db()
    result = UserProvisioningService(db).ensure_user(
        auth0_user_id="auth0|user-3",
        email="noname@example.com",
        name=None,
    )
    assert result.tenant_name == "noname@example.com"


def test_tenant_repo_finds_created_tenant_by_id():
    db = make_db()
    result = UserProvisioningService(db).ensure_user("auth0|u4", "u4@x.com", "U4")
    found = TenantRepository(db).find_by_id(result.tenant_id)
    assert found is not None
    assert found.id == result.tenant_id


def test_tenant_repo_finds_created_tenant_by_auth0_user_id():
    db = make_db()
    result = UserProvisioningService(db).ensure_user("auth0|u5", "u5@x.com", "U5")
    found = TenantRepository(db).find_by_auth0_user_id("auth0|u5")
    assert found is not None
    assert found.id == result.tenant_id
