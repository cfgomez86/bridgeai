"""
Unit test configuration and fixtures.
"""
from unittest.mock import MagicMock, patch

import pytest

from app.core.context import current_tenant_id, current_user_id

TEST_TENANT_ID = "test-tenant-00000000-0000-0000-0000-000000000001"
TEST_USER_ID = "test-user-00000000-0000-0000-0000-000000000001"
TEST_CONNECTION_ID = "test-conn-00000000-0000-0000-0000-000000000001"
TEST_CONNECTION_ID_B = "test-conn-00000000-0000-0000-0000-000000000002"


@pytest.fixture(autouse=True)
def set_tenant_context():
    """Automatically set tenant context for all unit tests that use repositories."""
    token_t = current_tenant_id.set(TEST_TENANT_ID)
    token_u = current_user_id.set(TEST_USER_ID)
    yield
    current_tenant_id.reset(token_t)
    current_user_id.reset(token_u)


@pytest.fixture(autouse=True)
def mock_httpx_async_client(request):
    """Mock httpx.AsyncClient only in ticket provider tests to avoid slow initialization."""
    test_path = request.node.fspath.strpath
    if "ticket_provider" in test_path or "test_jira_provider" in test_path or "test_azure_devops_provider" in test_path:
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value = MagicMock()
            yield mock_client
    else:
        yield
