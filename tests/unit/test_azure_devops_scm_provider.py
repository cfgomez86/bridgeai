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


class TestAzureDevOpsPATValidation:
    """Test PAT validation with scope and endpoint checking."""

    def test_validate_pat_success(self, provider):
        """Verify successful PAT validation."""
        mock_response = {
            "value": [
                {
                    "id": "user-1",
                    "displayName": "Alice Smith",
                    "uniqueName": "alice@example.com"
                }
            ]
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(mock_response).encode()
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            result = provider.validate_pat(
                "token-123",
                org_url="https://dev.azure.com/myorg"
            )

            assert "login" in result
            assert result["login"] is not None

    def test_validate_pat_missing_code_scope(self, provider):
        """Verify PAT lacking Code:Read scope is rejected."""
        # Simulate 404 or 403 on repos endpoint (missing Code scope)
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_error = HTTPError(
                url="https://dev.azure.com/myorg/_apis/git/repositories",
                code=403,
                msg="Forbidden",
                hdrs={},
                fp=None
            )
            mock_urlopen.side_effect = mock_error

            with pytest.raises(ValueError, match="scope|permission"):
                provider.validate_pat(
                    "token-123",
                    org_url="https://dev.azure.com/myorg"
                )

    def test_validate_pat_http_error(self, provider):
        """Verify HTTP errors are caught."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_error = HTTPError(
                url="https://dev.azure.com/myorg/_apis",
                code=401,
                msg="Unauthorized",
                hdrs={},
                fp=None
            )
            mock_urlopen.side_effect = mock_error

            with pytest.raises(ValueError, match="invalid|token"):
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

    def test_get_user_info_oauth(self, provider):
        """Verify get_user_info from OAuth token."""
        mock_response = {
            "value": [
                {
                    "displayName": "Alice Smith",
                    "uniqueName": "alice@example.com"
                }
            ]
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(mock_response).encode()
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            result = provider.get_user_info("token-123")

            assert "login" in result


class TestAzureDevOpsListProjects:
    """Test project listing with OAuth vs PAT dispatch."""

    def test_list_projects_pat(self, provider):
        """Verify list_projects with PAT."""
        mock_response = {
            "value": [
                {
                    "id": "proj-1",
                    "name": "MyProject",
                    "visibility": "public"
                }
            ]
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(mock_response).encode()
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            result = provider.list_projects(
                "token-123",
                org_url="https://dev.azure.com/myorg"
            )

            assert len(result) > 0

    def test_list_projects_oauth_iterates_accounts(self, provider):
        """Verify OAuth lists projects via profile + accessible accounts."""
        profile_response = {
            "value": [
                {
                    "id": "account-1",
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
                    "visibility": "public"
                }
            ]
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            def urlopen_side_effect(req, *args, **kwargs):
                resp = MagicMock()
                if "accounts" in req.full_url:
                    resp.read.return_value = json.dumps(profile_response).encode()
                else:
                    resp.read.return_value = json.dumps(projects_response).encode()
                resp.__enter__.return_value = resp
                return resp

            mock_urlopen.side_effect = urlopen_side_effect

            result = provider.list_projects("token-123")

            assert len(result) > 0


class TestAzureDevOpsListTree:
    """Test file tree traversal with error handling."""

    def test_list_tree_no_commits_error(self, provider):
        """Verify 'Cannot find any branches' error is handled gracefully."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            # Azure returns 404 with specific message for empty repos
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps({
                "message": "Cannot find any branches for the given repository."
            }).encode()
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            # Should handle gracefully
            with patch.object(provider, "_is_branch_not_found_error", return_value=True):
                with pytest.raises(ValueError):
                    provider.list_tree("token-123", "project/repo", "main", org_url="https://dev.azure.com/myorg")

    def test_list_tree_success(self, provider):
        """Verify successful tree listing."""
        tree_response = {
            "value": [
                {
                    "objectId": "blob-1",
                    "path": "src",
                    "isFolder": True
                },
                {
                    "objectId": "blob-2",
                    "path": "main.py",
                    "isFolder": False
                }
            ],
            "pagingToken": None
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(tree_response).encode()
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            result = provider.list_tree(
                "token-123",
                "project/repo",
                "main",
                org_url="https://dev.azure.com/myorg"
            )

            assert len(result) > 0
            paths = [item.get("path") for item in result]
            assert "main.py" in paths


class TestAzureDevOpsBasicAuth:
    """Test Basic auth header construction."""

    def test_pat_basic_auth_header(self, provider):
        """Verify Basic auth header uses token correctly."""
        mock_response = {
            "value": [
                {
                    "displayName": "Alice",
                    "uniqueName": "alice@example.com"
                }
            ]
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(mock_response).encode()
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            provider.validate_pat(
                "token-123",
                org_url="https://dev.azure.com/myorg"
            )

            call_args = mock_urlopen.call_args[0][0]
            auth_header = call_args.get_header("Authorization")
            # Azure DevOps uses ":<token>" as credentials
            expected = base64.b64encode(b":token-123").decode()
            assert auth_header == f"Basic {expected}"
