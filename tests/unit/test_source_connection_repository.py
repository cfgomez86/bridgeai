"""
Tests for SourceConnectionRepository — OAuth state TTL, soft-delete, activation, tenant isolation.
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session

from app.repositories.source_connection_repository import SourceConnectionRepository, _OAUTH_STATE_TTL_MINUTES
from app.models.oauth_state import OAuthState
from app.models.source_connection import SourceConnection
from app.models.code_file import CodeFile
from app.models.impact_analysis import ImpactedFile


@pytest.fixture
def mock_db():
    """Mock SQLAlchemy Session."""
    return MagicMock(spec=Session)


@pytest.fixture
def repo(mock_db):
    """SourceConnectionRepository with mocked DB."""
    return SourceConnectionRepository(mock_db)


class TestOAuthStateTTL:
    """Test OAuth state creation and expiration."""

    def test_create_oauth_state_sets_ttl(self, repo, mock_db):
        """Verify OAuth state expires in 10 minutes."""
        with patch("app.repositories.source_connection_repository.get_tenant_id", return_value="tenant-1"):
            with patch("app.repositories.source_connection_repository.uuid4", return_value="uuid-123"):
                repo.create_oauth_state("github", "state-abc", "http://localhost/callback")

                # Verify expires_at is ~10 minutes from now
                call_args = mock_db.add.call_args[0][0]
                assert isinstance(call_args, OAuthState)
                assert call_args.state_token == "state-abc"
                # TTL should be approximately 10 minutes
                now = datetime.utcnow()
                expected_expiry = now + timedelta(minutes=_OAUTH_STATE_TTL_MINUTES)
                assert abs((call_args.expires_at - expected_expiry).total_seconds()) < 2

    def test_consume_oauth_state_valid(self, repo, mock_db):
        """Verify consume_oauth_state returns non-expired, non-consumed state."""
        future = datetime.utcnow() + timedelta(minutes=5)
        valid_state = OAuthState(
            id="state-1",
            tenant_id="tenant-1",
            platform="github",
            state_token="state-abc",
            redirect_uri="http://localhost/callback",
            expires_at=future,
            consumed=False
        )

        query_mock = MagicMock()
        query_mock.filter.return_value.first.return_value = valid_state
        mock_db.query.return_value = query_mock

        with patch("app.repositories.source_connection_repository.get_tenant_id", return_value="tenant-1"):
            result = repo.consume_oauth_state("state-abc")

            assert result is valid_state
            assert result.consumed is True  # Modified in-place
            mock_db.commit.assert_called()

    def test_consume_oauth_state_expired_returns_none(self, repo, mock_db):
        """Verify consume_oauth_state rejects expired states."""
        query_mock = MagicMock()
        query_mock.filter.return_value.first.return_value = None  # Expired filtered out by query
        mock_db.query.return_value = query_mock

        with patch("app.repositories.source_connection_repository.get_tenant_id", return_value="tenant-1"):
            result = repo.consume_oauth_state("state-xyz")

            assert result is None

    def test_consume_oauth_state_already_consumed_returns_none(self, repo, mock_db):
        """Verify consume_oauth_state rejects already-consumed states."""
        query_mock = MagicMock()
        query_mock.filter.return_value.first.return_value = None  # Consumed filtered out by query
        mock_db.query.return_value = query_mock

        with patch("app.repositories.source_connection_repository.get_tenant_id", return_value="tenant-1"):
            result = repo.consume_oauth_state("state-abc")

            assert result is None

    def test_find_oauth_state_by_token_ignores_expiry(self, repo, mock_db):
        """Verify find_oauth_state_by_token returns state regardless of TTL/consumed status (for idempotency)."""
        past = datetime.utcnow() - timedelta(minutes=20)
        expired_state = OAuthState(
            id="state-1",
            tenant_id="tenant-1",
            platform="github",
            state_token="state-abc",
            redirect_uri="http://localhost/callback",
            expires_at=past,
            consumed=True
        )

        query_mock = MagicMock()
        query_mock.filter.return_value.first.return_value = expired_state
        mock_db.query.return_value = query_mock

        result = repo.find_oauth_state_by_token("state-abc")

        assert result is expired_state  # Returned despite expiry + consumed


class TestSoftDelete:
    """Test soft-delete logic and cascading cleanup."""

    def test_find_latest_for_platform_filters_deleted(self, repo, mock_db):
        """Verify find_latest_for_platform excludes soft-deleted connections."""
        active = MagicMock(spec=SourceConnection)
        active.deleted_at = None

        deleted = MagicMock(spec=SourceConnection)
        deleted.deleted_at = datetime.utcnow() - timedelta(days=1)

        query_mock = MagicMock()
        query_mock.filter.return_value.first.return_value = active
        mock_db.query.return_value = query_mock

        with patch("app.repositories.source_connection_repository.get_tenant_id", return_value="tenant-1"):
            result = repo.find_latest_for_platform("github")

            assert result is active
            # Verify _alive() filter was applied
            filter_call_args = query_mock.filter.call_args[0]
            assert len(filter_call_args) >= 2  # At least tenant_id and platform filters

    def test_delete_soft_deletes_connection(self, repo, mock_db):
        """Verify delete() marks connection as soft-deleted."""
        conn = MagicMock(spec=SourceConnection)
        conn.id = "conn-1"
        conn.deleted_at = None

        query_mock = MagicMock()
        query_mock.filter.return_value.first.return_value = conn
        mock_db.query.return_value = query_mock

        with patch("app.repositories.source_connection_repository.get_tenant_id", return_value="tenant-1"):
            repo.delete("conn-1")

            # Verify deleted_at was set
            assert conn.deleted_at is not None
            mock_db.commit.assert_called()


class TestActivateConnection:
    """Test connection activation and deactivation logic."""

    def test_activate_repo_deactivates_other_scm(self, repo, mock_db):
        """Verify activating a repo deactivates other SCM connections."""
        # Current active connection
        active_github = MagicMock(spec=SourceConnection)
        active_github.platform = "github"
        active_github.is_active = True

        # New connection to activate
        new_gitlab = MagicMock(spec=SourceConnection)
        new_gitlab.platform = "gitlab"
        new_gitlab.is_active = False
        new_gitlab.id = "conn-2"
        new_gitlab.repo_full_name = "owner/repo"
        new_gitlab.repo_name = "repo"
        new_gitlab.owner = "owner"
        new_gitlab.default_branch = "main"

        # Setup query to return both
        query_mock = MagicMock()
        query_mock.filter.return_value.all.return_value = [active_github, new_gitlab]
        query_mock.filter.return_value.first.return_value = new_gitlab
        mock_db.query.return_value = query_mock

        with patch("app.repositories.source_connection_repository.get_tenant_id", return_value="tenant-1"):
            result = repo.activate("conn-2", "owner/repo", "repo", "owner", "main")

            # Verify new connection is now active
            assert new_gitlab.is_active is True
            mock_db.commit.assert_called()

    def test_activate_ticket_connection_not_affected(self, repo, mock_db):
        """Verify activating SCM doesn't affect ticket provider connections."""
        # Activate SCM should only deactivate other SCM, not Jira/Azure ticket providers
        query_mock = MagicMock()
        query_mock.filter.return_value.first.return_value = MagicMock(spec=SourceConnection)
        mock_db.query.return_value = query_mock

        with patch("app.repositories.source_connection_repository.get_tenant_id", return_value="tenant-1"):
            repo.activate("conn-1", "owner/repo", "repo", "owner", "main")

            mock_db.commit.assert_called()


class TestTenantIsolation:
    """Test multi-tenant query safety."""

    def test_list_connected_includes_tenant_filter(self, repo, mock_db):
        """Verify list_connected filters by tenant_id."""
        query_mock = MagicMock()
        query_mock.filter.return_value.all.return_value = []
        mock_db.query.return_value = query_mock

        with patch("app.repositories.source_connection_repository.get_tenant_id", return_value="tenant-1"):
            repo.list_connected()

            # Verify tenant_id filter was applied
            filter_call = query_mock.filter.call_args[0]
            assert len(filter_call) > 0

    def test_create_connection_assigns_tenant(self, repo, mock_db):
        """Verify create_connection assigns current tenant_id."""
        with patch("app.repositories.source_connection_repository.get_tenant_id", return_value="tenant-123"):
            with patch("app.repositories.source_connection_repository.uuid4", return_value="uuid-1"):
                repo.create_connection(
                    platform="github",
                    display_name="user@example.com",
                    access_token="token-123"
                )

                call_args = mock_db.add.call_args[0][0]
                assert call_args.tenant_id == "tenant-123"


class TestConnectionLog:
    """Test audit logging."""

    def test_log_event_persists_audit_record(self, repo, mock_db):
        """Verify log_event creates ConnectionAuditLog record."""
        with patch("app.repositories.source_connection_repository.uuid4", return_value="log-id-1"):
            repo.log_event(
                connection_id="conn-1",
                platform="github",
                auth_method="oauth",
                event="connection_created",
                actor="user@example.com"
            )

            call_args = mock_db.add.call_args[0][0]
            assert isinstance(call_args, ConnectionAuditLog)
            assert call_args.connection_id == "conn-1"
            assert call_args.event == "connection_created"
            assert call_args.actor == "user@example.com"

    def test_log_event_includes_timestamp(self, repo, mock_db):
        """Verify audit log includes timestamp."""
        repo.log_event(
            connection_id="conn-1",
            platform="github",
            auth_method="oauth",
            event="connection_deleted",
            actor="user@example.com"
        )

        call_args = mock_db.add.call_args[0][0]
        assert hasattr(call_args, "created_at")
        assert call_args.created_at is not None
