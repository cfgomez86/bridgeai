"""
Tests for BitbucketProvider — Cloud vs Data Center dispatch, PAT validation, OAuth flow.
"""
import pytest
import json
import base64
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError

from app.services.scm_providers.bitbucket import BitbucketProvider


@pytest.fixture
def provider():
    """BitbucketProvider instance."""
    return BitbucketProvider()


class TestBitbucketCloudVsDCDispatch:
    """Test Cloud vs Data Center provider routing."""

    def test_is_dc_false_without_base_url(self, provider):
        """Verify _is_dc() returns False when base_url is None."""
        assert provider._is_dc(None) is False

    def test_is_dc_true_with_base_url(self, provider):
        """Verify _is_dc() returns True when base_url is set."""
        assert provider._is_dc("https://bitbucket.company.com") is True

    def test_validate_pat_dispatches_cloud(self, provider):
        """Verify validate_pat calls _validate_pat_cloud without base_url."""
        with patch.object(provider, "_validate_pat_cloud") as mock_cloud:
            mock_cloud.return_value = {"login": "user"}
            provider.validate_pat("token123", base_url=None)
            mock_cloud.assert_called_once()

    def test_validate_pat_dispatches_dc(self, provider):
        """Verify validate_pat calls _validate_pat_dc with base_url."""
        with patch.object(provider, "_validate_pat_dc") as mock_dc:
            mock_dc.return_value = {"login": "user"}
            provider.validate_pat("token123", base_url="https://bitbucket.company.com")
            mock_dc.assert_called_once()


class TestBitbucketCloudPATValidation:
    """Test Cloud PAT validation."""

    def test_validate_pat_cloud_success(self, provider):
        """Verify successful Cloud PAT validation."""
        mock_response = {
            "username": "alice",
            "display_name": "Alice"
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(mock_response).encode()
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            result = provider._validate_pat_cloud("token123")

            assert result["login"] == "alice"

    def test_validate_pat_cloud_fallback_to_account_id(self, provider):
        """Verify Cloud PAT validation falls back to account_id."""
        mock_response = {
            "account_id": "account-123",
            "display_name": "Alice"
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(mock_response).encode()
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            result = provider._validate_pat_cloud("token123")

            assert result["login"] == "account-123"

    def test_validate_pat_cloud_missing_login_raises_error(self, provider):
        """Verify error when Cloud response has no username/account_id."""
        mock_response = {"display_name": "Alice"}

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(mock_response).encode()
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            with pytest.raises(ValueError, match="did not return a valid user"):
                provider._validate_pat_cloud("token123")

    def test_validate_pat_cloud_http_error(self, provider):
        """Verify HTTP errors (401, 403) in Cloud are caught."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_error = HTTPError(
                url="https://api.bitbucket.org/2.0/user",
                code=401,
                msg="Unauthorized",
                hdrs={},
                fp=None
            )
            mock_urlopen.side_effect = mock_error

            with pytest.raises(ValueError, match="Bitbucket token invalid"):
                provider._validate_pat_cloud("bad_token")

    def test_validate_pat_cloud_bearer_header(self, provider):
        """Verify Cloud validation uses Bearer token in header."""
        mock_response = {"username": "alice"}

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(mock_response).encode()
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            provider._validate_pat_cloud("token123")

            call_args = mock_urlopen.call_args[0][0]
            auth_header = call_args.get_header("Authorization")
            assert auth_header == "Bearer token123"


class TestBitbucketDataCenterPATValidation:
    """Test Data Center PAT validation."""

    def test_validate_pat_dc_success(self, provider):
        """Verify successful DC PAT validation."""
        mock_response = {
            "name": "alice",
            "displayName": "Alice Smith"
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(mock_response).encode()
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            result = provider._validate_pat_dc("token123", "https://bitbucket.company.com")

            assert result["login"] == "alice"
            assert result["display_name"] == "Alice Smith"

    def test_validate_pat_dc_missing_name_raises_error(self, provider):
        """Verify error when DC response has no name."""
        mock_response = {"displayName": "Alice Smith"}

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(mock_response).encode()
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            with pytest.raises(ValueError, match="did not return a valid user"):
                provider._validate_pat_dc("token123", "https://bitbucket.company.com")

    def test_validate_pat_dc_strips_trailing_slash(self, provider):
        """Verify base_url trailing slash is stripped."""
        mock_response = {"name": "alice"}

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(mock_response).encode()
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            provider._validate_pat_dc("token123", "https://bitbucket.company.com/")

            call_args = mock_urlopen.call_args[0][0]
            url = call_args.full_url
            assert "//rest" not in url  # No double slash
            assert "/rest/api/1.0/users/~" in url

    def test_validate_pat_dc_http_error(self, provider):
        """Verify HTTP errors in DC are caught."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_error = HTTPError(
                url="https://bitbucket.company.com/rest/api/1.0/users/~",
                code=403,
                msg="Forbidden",
                hdrs={},
                fp=None
            )
            mock_urlopen.side_effect = mock_error

            with pytest.raises(ValueError, match="Data Center token invalid"):
                provider._validate_pat_dc("bad_token", "https://bitbucket.company.com")


class TestBitbucketOAuth:
    """Test OAuth flow."""

    def test_get_authorize_url_includes_required_params(self, provider):
        """Verify authorize URL has correct parameters."""
        url = provider.get_authorize_url(
            client_id="my-client",
            redirect_uri="http://localhost/callback",
            state="state-123"
        )

        assert "client_id=my-client" in url
        assert "state=state-123" in url
        assert "redirect_uri=http%3A%2F%2Flocalhost%2Fcallback" in url
        assert "scope=account+repository" in url

    def test_exchange_code_success(self, provider):
        """Verify successful OAuth token exchange."""
        mock_response = {
            "access_token": "access-token-123",
            "refresh_token": "refresh-token-456",
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

    def test_exchange_code_uses_basic_auth(self, provider):
        """Verify token exchange uses Basic auth with client credentials."""
        mock_response = {"access_token": "token"}

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(mock_response).encode()
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            provider.exchange_code(
                code="code-123",
                client_id="client-id",
                client_secret="client-secret",
                redirect_uri="http://localhost/callback"
            )

            call_args = mock_urlopen.call_args[0][0]
            auth_header = call_args.get_header("Authorization")
            expected_cred = base64.b64encode(b"client-id:client-secret").decode()
            assert auth_header == f"Basic {expected_cred}"

    def test_exchange_code_error_response(self, provider):
        """Verify error response in token exchange is detected."""
        mock_response = {
            "error": "invalid_grant",
            "error_description": "Authorization code expired"
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(mock_response).encode()
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            with pytest.raises(ValueError, match="Bitbucket OAuth error"):
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
            "display_name": "Alice"
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(mock_response).encode()
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            result = provider.get_user_info("token-123")

            assert result["login"] == "alice"
            assert result["name"] == "Alice"


class TestBitbucketHelpers:
    """Test utility methods."""

    def test_dc_api_validates_instance_url(self, provider):
        """Verify _dc_api validates instance URL."""
        with patch("app.services.scm_providers.bitbucket.validate_instance_url") as mock_validate:
            provider._dc_api("https://bitbucket.company.com")
            mock_validate.assert_called_once()

    def test_dc_api_returns_correct_rest_url(self, provider):
        """Verify _dc_api returns correct REST API URL."""
        url = provider._dc_api("https://bitbucket.company.com")
        assert url == "https://bitbucket.company.com/rest/api/1.0"

    def test_bearer_header_format(self, provider):
        """Verify _bearer() creates correct auth header."""
        headers = provider._bearer("token-123")
        assert headers["Authorization"] == "Bearer token-123"

    def test_parse_dc_full_name(self, provider):
        """Verify _parse_dc_full_name splits repo name correctly."""
        project, repo = provider._parse_dc_full_name("project/repo")
        assert project == "project"
        assert repo == "repo"

    def test_parse_dc_full_name_single_part(self, provider):
        """Verify _parse_dc_full_name handles single-part names."""
        project, repo = provider._parse_dc_full_name("repo")
        assert project == "repo"
        assert repo == "repo"
