"""Shared auth helpers for integration tests."""
from datetime import datetime

from fastapi import FastAPI

from app.core.auth0_auth import get_current_user
from app.core.context import current_tenant_id, current_user_id
from app.models.user import User

TEST_TENANT_ID = "test-tenant-00000000-0000-0000-0000-000000000001"
TEST_USER_ID = "test-user-00000000-0000-0000-0000-000000000001"


async def mock_auth() -> User:
    current_tenant_id.set(TEST_TENANT_ID)
    current_user_id.set(TEST_USER_ID)
    return User(
        id=TEST_USER_ID,
        auth0_user_id="auth0|test_user",
        tenant_id=TEST_TENANT_ID,
        email="test@bridgeai.test",
        name="Test User",
        role="admin",
        created_at=datetime.utcnow(),
    )


def apply_mock_auth(app: FastAPI) -> FastAPI:
    """Override Auth0 auth with a test user — call before TestClient(app)."""
    app.dependency_overrides[get_current_user] = mock_auth
    return app
