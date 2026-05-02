"""
Tests for GitLabProvider — OAuth, PAT validation, pagination, scope checking.
"""
import pytest
import json
import base64
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError

from app.services.scm_providers.gitlab import GitLabProvider


@pytest.fixture
def provider():
    """GitLabProvider instance."""
    return GitLabProvider()


class TestGitLabOAuth:
    """Test OAuth flow."""

    def test_get_authorize_url_includes_params(self, provider):
        """Verify authorize URL has required parameters."""
        url = provider.get_authorize_url(
            client_id="my-client",
            redirect_uri="http://localhost/callback",
            state="state-123"
        )

        assert "client_id=my-client" in url
        assert "redirect_uri=http%3A%2F%2Flocalhost%2Fcallback" in url
        assert "state=state-123" in url
        assert "api+read_user+read_repository" in url or "api" in url  # Check scopes

    def test_exchange_code_success(self, provider):
        """Verify successful OAuth token exchange."""
        mock_response = {
            "access_token": "token-123",
            "refresh_token": "refresh-456",
            "token_type": "Bearer",
            "expires_in": 3600,
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(mock_response).encode()
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            result = provider.exchange_code(
                code="code-123",
                client_id="client-id",
                client_secret="client-secret",
                redirect_uri="http://localhost/callback"
            )

            assert result["access_token"] == "token-123"
            assert result["refresh_token"] == "refresh-456"

    def test_exchange_code_error_response(self, provider):
        """Verify error in token exchange is raised."""
        mock_response = {
            "error": "invalid_grant",
            "error_description": "Code expired"
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(mock_response).encode()
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            with pytest.raises(ValueError):
                provider.exchange_code(
                    code="bad-code",
                    client_id="client-id",
                    client_secret="client-secret",
                    redirect_uri="http://localhost/callback"
                )

    def test_get_user_info(self, provider):
        """Verify get_user_info returns login and name."""
        mock_response = {
            "username": "alice",
            "name": "Alice Smith"
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(mock_response).encode()
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            result = provider.get_user_info("token-123")

            assert result["login"] == "alice"
            assert result["name"] == "Alice Smith"


class TestGitLabPATValidation:
    """Test PAT validation with scope checking."""

    def test_validate_pat_success(self, provider):
        """Verify successful PAT validation."""
        mock_response = {
            "username": "alice",
            "name": "Alice",
            "scopes": ["read_api", "read_user", "read_repository"]
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(mock_response).encode()
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            result = provider.validate_pat("token-123")

            assert result["login"] == "alice"

    def test_validate_pat_missing_scope_raises_error(self, provider):
        """Verify PAT lacking required scopes is rejected."""
        mock_response = {
            "username": "alice",
            "scopes": ["read_user"]  # Missing api scope
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(mock_response).encode()
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            with pytest.raises(ValueError, match="scope"):
                provider.validate_pat("token-123")

    def test_validate_pat_with_base_url(self, provider):
        """Verify self-hosted instance URL is used."""
        mock_response = {
            "username": "alice",
            "scopes": ["read_api", "read_user", "read_repository"]
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(mock_response).encode()
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            provider.validate_pat("token-123", base_url="https://gitlab.company.com")

            call_args = mock_urlopen.call_args[0][0]
            assert "gitlab.company.com" in call_args.full_url

    def test_validate_pat_http_error(self, provider):
        """Verify HTTP errors are caught."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_error = HTTPError(
                url="https://gitlab.com/api/v4/user",
                code=401,
                msg="Unauthorized",
                hdrs={},
                fp=None
            )
            mock_urlopen.side_effect = mock_error

            with pytest.raises(ValueError, match="GitLab PAT invalid"):
                provider.validate_pat("bad-token")


class TestGitLabListRepos:
    """Test repository listing with pagination."""

    def test_list_repos_pagination(self, provider):
        """Verify list_repos handles pagination correctly."""
        page1 = [
            {"id": i, "name": f"repo{i}", "path_with_namespace": f"user/repo{i}",
             "default_branch": "main", "visibility": "public", "namespace": {"path": "user"}}
            for i in range(100)
        ]
        page2 = [
            {"id": 100, "name": "repo100", "path_with_namespace": "user/repo100",
             "default_branch": "main", "visibility": "public", "namespace": {"path": "user"}},
        ]

        with patch("urllib.request.urlopen") as mock_urlopen:
            def urlopen_side_effect(req, *args, **kwargs):
                resp = MagicMock()
                if "page=2" in req.full_url:
                    resp.read.return_value = json.dumps(page2).encode()
                else:
                    resp.read.return_value = json.dumps(page1).encode()
                resp.__enter__.return_value = resp
                return resp

            mock_urlopen.side_effect = urlopen_side_effect

            result = provider.list_repos("token-123")

            assert len(result) == 101
            assert result[0]["name"] == "repo0"
            assert result[100]["name"] == "repo100"

    def test_list_repos_empty(self, provider):
        """Verify empty repo list is handled."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps([]).encode()
            mock_resp.headers = {}
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            result = provider.list_repos("token-123")

            assert result == []


class TestGitLabListTree:
    """Test file tree traversal with recursion and pagination."""

    def test_list_tree_recursive_traversal(self, provider):
        """Verify list_tree returns all blobs via recursive=true query."""
        tree_response = [
            {
                "id": "blob-sha-1",
                "name": "main.py",
                "path": "main.py",
                "type": "blob",
                "mode": "100644"
            },
            {
                "id": "blob-sha-2",
                "name": "app.py",
                "path": "src/app.py",
                "type": "blob",
                "mode": "100644"
            },
        ]

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(tree_response).encode()
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            result = provider.list_tree("token-123", "user/repo", "main")

            # Should include both files
            assert any("main.py" in item.path for item in result)
            assert any("src/app.py" in item.path for item in result)
