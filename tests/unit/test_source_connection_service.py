"""
Tests for SourceConnectionService — OAuth flow, PAT validation, tenant isolation.
"""
import pytest
import uuid
from unittest.mock import MagicMock, patch, PropertyMock

from app.services.source_connection_service import SourceConnectionService
from app.repositories.source_connection_repository import SourceConnectionRepository
from app.domain.source_connection import SourceConnection
from app.core.config import Settings
from app.models.source_connection import SourceConnection as SourceConnectionORM


@pytest.fixture
def mock_repo():
    """Mock SourceConnectionRepository."""
    return MagicMock(spec=SourceConnectionRepository)


@pytest.fixture
def settings():
    """Settings with OAuth credentials configured."""
    return Settings(
        DATABASE_URL="sqlite:///:memory:",
        GITHUB_CLIENT_ID="github-client-id",
        GITHUB_CLIENT_SECRET="github-client-secret",
        GITLAB_CLIENT_ID="gitlab-client-id",
        GITLAB_CLIENT_SECRET="gitlab-client-secret",
        AZURE_DEVOPS_CLIENT_ID="azure-client-id",
        AZURE_DEVOPS_CLIENT_SECRET="azure-client-secret",
        BITBUCKET_CLIENT_ID="bitbucket-client-id",
        BITBUCKET_CLIENT_SECRET="bitbucket-client-secret",
        JIRA_CLIENT_ID="jira-client-id",
        JIRA_CLIENT_SECRET="jira-client-secret",
    )


@pytest.fixture
def service(mock_repo, settings):
    """SourceConnectionService with mocked repo and settings."""
    return SourceConnectionService(mock_repo, settings)


class TestOAuthFlow:
    """Test OAuth authorization and callback handling."""

    def test_get_authorize_url_generates_unique_state(self, service, mock_repo):
        """Verify get_authorize_url creates unique state and stores it."""
        with patch("app.services.source_connection_service.get_provider") as mock_get_provider:
            mock_provider = MagicMock()
            mock_provider.get_authorize_url.return_value = "https://github.com/auth?state=xyz"
            mock_get_provider.return_value = mock_provider

            url1 = service.get_authorize_url("github", "http://localhost/callback")
            url2 = service.get_authorize_url("github", "http://localhost/callback")

            assert mock_repo.create_oauth_state.call_count == 2
            assert url1 == "https://github.com/auth?state=xyz"
            assert url2 == "https://github.com/auth?state=xyz"

    def test_handle_callback_restores_tenant_context(self, service, mock_repo):
        """Verify handle_callback sets tenant_id from OAuth state."""
        oauth_state = MagicMock()
        oauth_state.tenant_id = "tenant-123"
        oauth_state.redirect_uri = "http://localhost/callback"
        mock_repo.consume_oauth_state.return_value = oauth_state

        mock_connection_orm = MagicMock(spec=SourceConnectionORM)
        mock_connection_orm.id = "conn-1"
        mock_connection_orm.platform = "github"
        mock_repo.create_connection.return_value = mock_connection_orm

        with patch("app.services.source_connection_service.get_provider") as mock_get_provider:
            mock_provider = MagicMock()
            mock_provider.exchange_code.return_value = {
                "access_token": "token-123",
                "refresh_token": None
            }
            mock_provider.get_user_info.return_value = {"login": "user1"}
            mock_get_provider.return_value = mock_provider

            with patch("app.core.context.current_tenant_id") as mock_tenant:
                result = service.handle_callback("github", "code-123", "state-xyz")

                # Verify tenant was set from OAuth state
                mock_tenant.set.assert_called_with("tenant-123")
                assert isinstance(result, SourceConnection)

    def test_handle_callback_duplicate_state_returns_existing_connection(self, service, mock_repo):
        """Verify duplicate callback (state already consumed) returns existing connection."""
        # First callback: state not found (already consumed)
        mock_repo.consume_oauth_state.return_value = None

        # Existing state record found
        past_state = MagicMock()
        past_state.tenant_id = "tenant-123"
        mock_repo.find_oauth_state_by_token.return_value = past_state

        # Existing connection
        existing_conn_orm = MagicMock(spec=SourceConnectionORM)
        existing_conn_orm.id = "conn-existing"
        existing_conn_orm.platform = "github"
        mock_repo.find_latest_for_platform.return_value = existing_conn_orm

        with patch("app.core.context.current_tenant_id") as mock_tenant:
            result = service.handle_callback("github", "code-123", "state-xyz")

            # Verify tenant was restored
            mock_tenant.set.assert_called_with("tenant-123")
            # Verify existing connection was returned
            assert result is not None

    def test_handle_callback_invalid_state_raises_error(self, service, mock_repo):
        """Verify invalid/expired state raises ValueError."""
        mock_repo.consume_oauth_state.return_value = None
        mock_repo.find_oauth_state_by_token.return_value = None

        with pytest.raises(ValueError, match="Invalid or expired OAuth state"):
            service.handle_callback("github", "code-123", "state-xyz")

    def test_handle_callback_provider_error_raises_error(self, service, mock_repo):
        """Verify provider token exchange errors are wrapped."""
        oauth_state = MagicMock()
        oauth_state.tenant_id = "tenant-123"
        oauth_state.redirect_uri = "http://localhost/callback"
        mock_repo.consume_oauth_state.return_value = oauth_state

        with patch("app.services.source_connection_service.get_provider") as mock_get_provider:
            mock_provider = MagicMock()
            mock_provider.exchange_code.side_effect = Exception("Network error")
            mock_get_provider.return_value = mock_provider

            with patch("app.core.context.current_tenant_id"):
                with pytest.raises(ValueError, match="OAuth token exchange failed"):
                    service.handle_callback("github", "code-123", "state-xyz")

    def test_handle_callback_logs_event(self, service, mock_repo):
        """Verify connection creation is logged with audit trail."""
        oauth_state = MagicMock()
        oauth_state.tenant_id = "tenant-123"
        oauth_state.redirect_uri = "http://localhost/callback"
        mock_repo.consume_oauth_state.return_value = oauth_state

        mock_connection_orm = MagicMock(spec=SourceConnectionORM)
        mock_connection_orm.id = "conn-1"
        mock_connection_orm.platform = "github"
        mock_repo.create_connection.return_value = mock_connection_orm

        with patch("app.services.source_connection_service.get_provider") as mock_get_provider:
            mock_provider = MagicMock()
            mock_provider.exchange_code.return_value = {
                "access_token": "token-123",
                "refresh_token": None
            }
            mock_provider.get_user_info.return_value = {"login": "alice"}
            mock_get_provider.return_value = mock_provider

            with patch("app.core.context.current_tenant_id"):
                service.handle_callback("github", "code-123", "state-xyz")

                # Verify event logged
                mock_repo.log_event.assert_called_once()
                call_args = mock_repo.log_event.call_args
                assert call_args[1]["event"] == "connection_created"
                assert call_args[1]["auth_method"] == "oauth"
                assert call_args[1]["actor"] == "alice"


class TestPATConnection:
    """Test PAT validation and creation."""

    def test_create_pat_connection_github(self, service, mock_repo):
        """Verify PAT creation calls validate_pat and stores token."""
        with patch("app.services.source_connection_service.get_provider") as mock_get_provider:
            mock_provider = MagicMock()
            mock_provider.validate_pat.return_value = {"login": "user1"}
            mock_get_provider.return_value = mock_provider

            mock_connection_orm = MagicMock(spec=SourceConnectionORM)
            mock_connection_orm.id = "conn-2"
            mock_connection_orm.platform = "github"
            mock_repo.create_connection.return_value = mock_connection_orm

            result = service.create_pat_connection("github", "ghp_token123")

            mock_provider.validate_pat.assert_called_once()
            mock_repo.create_connection.assert_called_once()
            call_args = mock_repo.create_connection.call_args
            assert call_args[1]["auth_method"] == "pat"
            assert call_args[1]["access_token"] == "ghp_token123"
            assert result is not None

    def test_create_pat_connection_with_base_url(self, service, mock_repo):
        """Verify base_url is passed for self-hosted instances."""
        with patch("app.services.source_connection_service.get_provider") as mock_get_provider:
            mock_provider = MagicMock()
            mock_provider.validate_pat.return_value = {"login": "user1"}
            mock_get_provider.return_value = mock_provider

            mock_connection_orm = MagicMock(spec=SourceConnectionORM)
            mock_repo.create_connection.return_value = mock_connection_orm

            service.create_pat_connection(
                "github",
                "ghp_token123",
                base_url="https://github.company.com"
            )

            call_args = mock_repo.create_connection.call_args
            assert call_args[1]["base_url"] == "https://github.company.com"

    def test_create_pat_connection_validation_error(self, service, mock_repo):
        """Verify validation errors are wrapped."""
        with patch("app.services.source_connection_service.get_provider") as mock_get_provider:
            mock_provider = MagicMock()
            mock_provider.validate_pat.side_effect = ValueError("Invalid scope")
            mock_get_provider.return_value = mock_provider

            with pytest.raises(ValueError, match="PAT validation failed"):
                service.create_pat_connection("github", "bad_token")


class TestListConnections:
    """Test listing and managing connections."""

    def test_list_connections_returns_domain_objects(self, service, mock_repo):
        """Verify list_connections converts ORM to domain objects."""
        from datetime import datetime

        orm1 = MagicMock(spec=SourceConnectionORM)
        orm1.id = "conn-1"
        orm1.platform = "github"
        orm2 = MagicMock(spec=SourceConnectionORM)
        orm2.id = "conn-2"
        orm2.platform = "gitlab"
        mock_repo.list_connected.return_value = [orm1, orm2]

        with patch.object(SourceConnectionRepository, "to_domain") as mock_to_domain:
            mock_to_domain.side_effect = [
                SourceConnection(
                    id="conn-1",
                    platform="github",
                    display_name="user1",
                    repo_full_name="owner/repo",
                    repo_name="repo",
                    owner="owner",
                    default_branch="main",
                    is_active=True,
                    created_at=datetime.now()
                ),
                SourceConnection(
                    id="conn-2",
                    platform="gitlab",
                    display_name="user2",
                    repo_full_name="owner/repo",
                    repo_name="repo",
                    owner="owner",
                    default_branch="main",
                    is_active=True,
                    created_at=datetime.now()
                ),
            ]

            result = service.list_connections()

            assert len(result) == 2
            assert result[0].id == "conn-1"
            assert result[1].id == "conn-2"

    def test_delete_connection_logs_event(self, service, mock_repo):
        """Verify delete_connection logs the deletion event."""
        conn_orm = MagicMock(spec=SourceConnectionORM)
        conn_orm.id = "conn-1"
        conn_orm.platform = "github"
        conn_orm.auth_method = "oauth"
        conn_orm.display_name = "alice"
        mock_repo.find_by_id.return_value = conn_orm
        mock_repo.delete.return_value = True

        service.delete_connection("conn-1")

        mock_repo.log_event.assert_called_once()
        call_args = mock_repo.log_event.call_args
        assert call_args[1]["event"] == "connection_deleted"
        assert call_args[1]["actor"] == "alice"
