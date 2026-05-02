"""
Tests for JiraOAuthProvider — PAT validation, OAuth exchange, error handling.
"""
import pytest
import json
import base64
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError

from app.services.ticket_providers.jira_oauth import JiraOAuthProvider


@pytest.fixture
def provider():
    """JiraOAuthProvider instance."""
    return JiraOAuthProvider()


class TestJiraOAuthPATValidation:
    """Test PAT validation for Jira API tokens."""

    def test_validate_pat_requires_base_url(self, provider):
        """Verify base_url is required; raises ValueError if missing."""
        with pytest.raises(ValueError, match="base_url is required"):
            provider.validate_pat("token123", email="user@example.com")

    def test_validate_pat_requires_email(self, provider):
        """Verify email is required; raises ValueError if missing."""
        with pytest.raises(ValueError, match="email is required"):
            provider.validate_pat("token123", base_url="https://org.atlassian.net")

    def test_validate_pat_success_with_email_address(self, provider):
        """Verify successful validation with emailAddress in response."""
        mock_response = {
            "emailAddress": "user@example.com",
            "displayName": "John Doe",
            "accountId": "abc123",
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(mock_response).encode()
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            result = provider.validate_pat(
                "token123",
                base_url="https://org.atlassian.net",
                email="user@example.com"
            )

            assert result["login"] == "user@example.com"
            assert result["display_name"] == "John Doe"

    def test_validate_pat_fallback_to_account_id(self, provider):
        """Verify accountId is used if emailAddress missing."""
        mock_response = {
            "accountId": "abc123",
            "displayName": "John Doe",
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(mock_response).encode()
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            result = provider.validate_pat(
                "token123",
                base_url="https://org.atlassian.net",
                email="user@example.com"
            )

            assert result["login"] == "abc123"
            assert result["display_name"] == "John Doe"

    def test_validate_pat_builds_basic_auth_header(self, provider):
        """Verify Basic auth header is correctly formatted."""
        mock_response = {"emailAddress": "user@example.com", "displayName": "User"}

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(mock_response).encode()
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            provider.validate_pat(
                "token123",
                base_url="https://org.atlassian.net",
                email="user@example.com"
            )

            # Get the request passed to urlopen
            call_args = mock_urlopen.call_args[0][0]
            auth_header = call_args.get_header("Authorization")

            # Verify Basic auth format
            expected_cred = base64.b64encode(b"user@example.com:token123").decode()
            assert auth_header == f"Basic {expected_cred}"

    def test_validate_pat_http_error(self, provider):
        """Verify HTTP errors (401, 403, etc.) are caught and wrapped."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_error = HTTPError(
                url="https://org.atlassian.net/rest/api/3/myself",
                code=401,
                msg="Unauthorized",
                hdrs={},
                fp=None
            )
            mock_urlopen.side_effect = mock_error

            with pytest.raises(ValueError, match="Jira API token invalid: HTTP 401"):
                provider.validate_pat(
                    "bad_token",
                    base_url="https://org.atlassian.net",
                    email="user@example.com"
                )

    def test_validate_pat_network_error(self, provider):
        """Verify network errors are caught and wrapped."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = TimeoutError("Connection timed out")

            with pytest.raises(ValueError, match="Jira API token validation failed"):
                provider.validate_pat(
                    "token123",
                    base_url="https://org.atlassian.net",
                    email="user@example.com"
                )

    def test_validate_pat_missing_user_info(self, provider):
        """Verify error when response has no emailAddress or accountId."""
        mock_response = {
            "displayName": "User",
            # Missing emailAddress and accountId
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(mock_response).encode()
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            with pytest.raises(ValueError, match="did not return a valid user"):
                provider.validate_pat(
                    "token123",
                    base_url="https://org.atlassian.net",
                    email="user@example.com"
                )

    def test_validate_pat_strips_trailing_slash_from_base_url(self, provider):
        """Verify base_url trailing slash is stripped."""
        mock_response = {"emailAddress": "user@example.com", "displayName": "User"}

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(mock_response).encode()
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            provider.validate_pat(
                "token123",
                base_url="https://org.atlassian.net/",  # trailing slash
                email="user@example.com"
            )

            call_args = mock_urlopen.call_args[0][0]
            # Verify URL has no double slash before /rest
            assert "//rest" not in call_args.full_url


class TestJiraOAuthAuthorization:
    """Test OAuth authorization URL generation."""

    def test_get_authorize_url_includes_required_params(self, provider):
        """Verify authorize URL includes client_id, scope, state, etc."""
        url = provider.get_authorize_url(
            client_id="my-client-id",
            redirect_uri="http://localhost/callback",
            state="state-xyz"
        )

        assert "client_id=my-client-id" in url
        assert "redirect_uri=http%3A%2F%2Flocalhost%2Fcallback" in url
        assert "state=state-xyz" in url
        assert "scope=read%3Ajira-work" in url
        assert "audience=api.atlassian.com" in url

    def test_get_authorize_url_correct_endpoint(self, provider):
        """Verify authorize URL points to correct Atlassian endpoint."""
        url = provider.get_authorize_url("client-id", "http://localhost/cb", "state")
        assert url.startswith("https://auth.atlassian.com/authorize?")


class TestJiraOAuthExchange:
    """Test OAuth token exchange."""

    def test_exchange_code_success(self, provider):
        """Verify successful token exchange."""
        mock_response = {
            "access_token": "access-token-123",
            "refresh_token": "refresh-token-456",
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

            assert result["access_token"] == "access-token-123"
            assert result["refresh_token"] == "refresh-token-456"

    def test_exchange_code_error_in_response(self, provider):
        """Verify error response is detected and raised."""
        mock_response = {
            "error": "invalid_grant",
            "error_description": "The authorization code has expired",
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

    def test_exchange_code_network_error(self, provider):
        """Verify network errors during token exchange are wrapped."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = Exception("Connection refused")

            with pytest.raises(Exception):
                provider.exchange_code(
                    code="code-123",
                    client_id="client-id",
                    client_secret="client-secret",
                    redirect_uri="http://localhost/callback"
                )
