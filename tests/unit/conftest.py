"""
Unit test configuration and fixtures.
"""
import pytest

from app.core.context import current_tenant_id, current_user_id

TEST_TENANT_ID = "test-tenant-00000000-0000-0000-0000-000000000001"
TEST_USER_ID = "test-user-00000000-0000-0000-0000-000000000001"


@pytest.fixture(autouse=True)
def set_tenant_context():
    """Automatically set tenant context for all unit tests that use repositories."""
    token_t = current_tenant_id.set(TEST_TENANT_ID)
    token_u = current_user_id.set(TEST_USER_ID)
    yield
    current_tenant_id.reset(token_t)
    current_user_id.reset(token_u)
