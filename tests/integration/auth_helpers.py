"""Shared auth helpers for integration tests."""
from datetime import datetime

from fastapi import FastAPI

from app.core.auth0_auth import get_current_user
from app.core.context import current_tenant_id, current_user_id
from app.models.user import User

TEST_TENANT_ID = "test-tenant-00000000-0000-0000-0000-000000000001"
TEST_USER_ID = "test-user-00000000-0000-0000-0000-000000000001"
TEST_CONNECTION_ID = "test-conn-00000000-0000-0000-0000-000000000001"


def seed_source_connection(session, connection_id: str = TEST_CONNECTION_ID) -> None:
    """Insertar una SourceConnection para que las rutas que validan con
    SourceConnectionRepository.find_by_id() no devuelvan 404."""
    from app.models.source_connection import SourceConnection
    conn = SourceConnection(
        id=connection_id,
        tenant_id=TEST_TENANT_ID,
        platform="github",
        display_name="Test Connection",
        access_token="test-token",
        refresh_token=None,
        owner="testuser",
        repo_name="repo",
        repo_full_name="testuser/repo",
        default_branch="main",
        is_active=True,
        created_at=datetime.utcnow(),
    )
    session.add(conn)
    session.commit()


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
