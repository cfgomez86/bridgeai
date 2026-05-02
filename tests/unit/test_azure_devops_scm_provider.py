"""
Tests for Azure DevOps SCM Provider — dual-auth (OAuth/PAT), scope probing, multi-account enumeration.
"""
import pytest
import json
import base64
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError

from app.services.scm_providers.azure_devops import AzureDevOpsProvider


@pytest.fixture
def provider():
    """AzureDevOpsProvider instance."""
    return AzureDevOpsProvider()


def _make_resp(data: dict) -> MagicMock:
    resp = MagicMock()
    resp.read.return_value = json.dumps(data).encode()
    resp.__enter__.return_value = resp
    return resp


class TestAzureDevOpsPATValidation:
    """Test PAT validation with scope and endpoint checking."""

    def test_validate_pat_success(self, provider):
        """Verify successful PAT validation."""
        projects_data = {"value": [{"id": "proj-1", "name": "MyProject"}]}

        with patch("urllib.request.urlopen") as mock_urlopen:
            def side_effect(req, *args, **kwargs):
                if "_apis/projects" in req.full_url:
                    return _make_resp(projects_data)
                return _make_resp({})

            mock_urlopen.side_effect = side_effect

            result = provider.validate_pat(
                "token-123",
                org_url="https://dev.azure.com/myorg"
            )

            assert "login" in result
            assert result["login"] is not None

    def test_validate_pat_missing_code_scope(self, provider):
        """Verify PAT lacking Code:Read scope is rejected."""
        projects_data = {"value": [{"id": "proj-1", "name": "MyProject"}]}

        with patch("urllib.request.urlopen") as mock_urlopen:
            def side_effect(req, *args, **kwargs):
                url = req.full_url
                if "git/repositories" in url:
                    raise HTTPError(url=url, code=403, msg="Forbidden", hdrs={}, fp=None)
                return _make_resp(projects_data)

            mock_urlopen.side_effect = side_effect

            with pytest.raises(ValueError, match="Code"):
                provider.validate_pat(
                    "token-123",
                    org_url="https://dev.azure.com/myorg"
                )

    def test_validate_pat_http_error(self, provider):
        """Verify HTTP errors are caught."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_error = HTTPError(
                url="https://dev.azure.com/myorg/_apis/projects",
                code=401,
                msg="Unauthorized",
                hdrs={},
                fp=None
            )
            mock_urlopen.side_effect = mock_error

            with pytest.raises(ValueError, match="Azure DevOps PAT invalid"):
                provider.validate_pat(
                    "bad-token",
                    org_url="https://dev.azure.com/myorg"
                )


class TestAzureDevOpsOAuth:
    """Test OAuth flow."""

    def test_get_authorize_url_includes_params(self, provider):
        """Verify authorize URL has required parameters."""
        url = provider.get_authorize_url(
            client_id="my-client",
            redirect_uri="http://localhost/callback",
            state="state-123"
        )

        assert "client_id=my-client" in url
        assert "state=state-123" in url

    def test_exchange_code_success(self, provider):
        """Verify successful OAuth token exchange."""
        mock_response = {
            "access_token": "token-123",
            "token_type": "bearer",
            "expires_in": 3600,
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = _make_resp(mock_response)

            result = provider.exchange_code(
                code="code-123",
                client_id="client-id",
                client_secret="client-secret",
                redirect_uri="http://localhost/callback"
            )

            assert result["access_token"] == "token-123"

    def test_get_user_info_oauth(self, provider):
        """Verify get_user_info from OAuth token."""
        mock_response = {
            "emailAddress": "alice@example.com",
            "displayName": "Alice Smith"
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = _make_resp(mock_response)

            result = provider.get_user_info("token-123")

            assert "login" in result


class TestAzureDevOpsListProjects:
    """Test project listing with OAuth vs PAT dispatch."""

    def test_list_projects_pat(self, provider):
        """Verify list_projects with PAT."""
        projects_data = {
            "value": [
                {
                    "id": "proj-1",
                    "name": "MyProject",
                    "capabilities": {"processTemplate": {"templateName": "Agile"}}
                }
            ]
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = _make_resp(projects_data)

            result = provider.list_projects(
                "token-123",
                org_url="https://dev.azure.com/myorg"
            )

            assert len(result) > 0

    def test_list_projects_oauth_iterates_accounts(self, provider):
        """Verify OAuth lists projects via profile + accessible accounts."""
        profile_response = {"id": "user-123", "displayName": "Alice", "emailAddress": "alice@example.com"}
        accounts_response = {
            "value": [
                {
                    "accountName": "myorg",
                    "accountUri": "https://dev.azure.com/myorg"
                }
            ]
        }
        projects_response = {
            "value": [
                {
                    "id": "proj-1",
                    "name": "MyProject",
                    "capabilities": {"processTemplate": {"templateName": "Agile"}}
                }
            ]
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            def urlopen_side_effect(req, *args, **kwargs):
                url = req.full_url
                if "profiles/me" in url:
                    return _make_resp(profile_response)
                if "accounts" in url:
                    return _make_resp(accounts_response)
                return _make_resp(projects_response)

            mock_urlopen.side_effect = urlopen_side_effect

            # Use eyJ prefix to trigger OAuth path
            result = provider.list_projects("eyJfaketoken")

            assert len(result) > 0


class TestAzureDevOpsListTree:
    """Test file tree traversal with error handling."""

    def test_list_tree_no_commits_error(self, provider):
        """Verify 'Cannot find any branches' error is handled gracefully."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            error = HTTPError(
                url="https://dev.azure.com/org/project/_apis/git/repositories/repo/items",
                code=404,
                msg="Not Found",
                hdrs={},
                fp=MagicMock(read=MagicMock(return_value=b"Cannot find any branches for the given repository."))
            )
            error.read = MagicMock(return_value=b"Cannot find any branches for the given repository.")
            mock_urlopen.side_effect = error

            with pytest.raises(RuntimeError):
                provider.list_tree("token-123", "org/project/repo", "main")

    def test_list_tree_success(self, provider):
        """Verify successful tree listing."""
        tree_response = {
            "value": [
                {
                    "objectId": "blob-1",
                    "path": "/src",
                    "gitObjectType": "tree"
                },
                {
                    "objectId": "blob-2",
                    "path": "/main.py",
                    "gitObjectType": "blob"
                }
            ]
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = _make_resp(tree_response)

            result = provider.list_tree(
                "token-123",
                "myorg/myproject/myrepo",
                "main"
            )

            assert len(result) > 0
            paths = [item.path for item in result]
            assert any("main.py" in p for p in paths)


class TestAzureDevOpsBasicAuth:
    """Test Basic auth header construction."""

    def test_pat_basic_auth_header(self, provider):
        """Verify Basic auth header uses token correctly."""
        projects_data = {"value": [{"id": "proj-1", "name": "MyProject"}]}

        with patch("urllib.request.urlopen") as mock_urlopen:
            def side_effect(req, *args, **kwargs):
                if "_apis/projects" in req.full_url:
                    return _make_resp(projects_data)
                return _make_resp({})

            mock_urlopen.side_effect = side_effect

            provider.validate_pat(
                "token-123",
                org_url="https://dev.azure.com/myorg"
            )

            call_args = mock_urlopen.call_args_list[0][0][0]
            auth_header = call_args.get_header("Authorization")
            # Azure DevOps uses ":<token>" as credentials
            expected = base64.b64encode(b":token-123").decode()
            assert auth_header == f"Basic {expected}"
