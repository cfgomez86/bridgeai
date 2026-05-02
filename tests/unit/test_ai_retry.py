import httpx
import pytest

from app.utils.ai_retry import is_retryable_error


class TestIsRetryableError:
    """Test is_retryable_error() with network errors, SDK exceptions, and status codes."""

    # --- Built-in exception types (httpx, stdlib) ---

    def test_httpx_request_error_is_retryable(self):
        exc = httpx.RequestError("Connection failed")
        assert is_retryable_error(exc) is True

    def test_timeout_error_is_retryable(self):
        exc = TimeoutError("Request timed out")
        assert is_retryable_error(exc) is True

    def test_connection_error_is_retryable(self):
        exc = ConnectionError("Connection refused")
        assert is_retryable_error(exc) is True

    # --- SDK exception names (matched by type.__name__) ---

    def test_api_connection_error_by_name(self):
        """APIConnectionError from anthropic/openai SDKs is retryable."""
        exc = type("APIConnectionError", (Exception,), {})()
        assert is_retryable_error(exc) is True

    def test_api_timeout_error_by_name(self):
        """APITimeoutError from anthropic/openai SDKs is retryable."""
        exc = type("APITimeoutError", (Exception,), {})()
        assert is_retryable_error(exc) is True

    def test_rate_limit_error_by_name(self):
        """RateLimitError from anthropic/openai SDKs is retryable."""
        exc = type("RateLimitError", (Exception,), {})()
        assert is_retryable_error(exc) is True

    def test_internal_server_error_by_name(self):
        """InternalServerError from anthropic/openai SDKs is retryable."""
        exc = type("InternalServerError", (Exception,), {})()
        assert is_retryable_error(exc) is True

    def test_service_unavailable_error_by_name(self):
        """ServiceUnavailableError from anthropic/openai SDKs is retryable."""
        exc = type("ServiceUnavailableError", (Exception,), {})()
        assert is_retryable_error(exc) is True

    def test_google_genai_server_error_by_name(self):
        """ServerError from google-genai SDK is retryable."""
        exc = type("ServerError", (Exception,), {})()
        assert is_retryable_error(exc) is True

    def test_google_genai_deadline_exceeded_by_name(self):
        """DeadlineExceeded from google-genai SDK is retryable."""
        exc = type("DeadlineExceeded", (Exception,), {})()
        assert is_retryable_error(exc) is True

    # --- Status codes: 429 (rate limit) is retryable ---

    def test_status_429_is_retryable_via_status_code(self):
        """429 Too Many Requests is retryable."""
        exc = type("HTTPException", (Exception,), {"status_code": 429})()
        assert is_retryable_error(exc) is True

    def test_status_429_is_retryable_via_code(self):
        """429 Too Many Requests via 'code' attribute is retryable."""
        exc = type("HTTPException", (Exception,), {"code": 429})()
        assert is_retryable_error(exc) is True

    # --- Status codes: 5xx are retryable ---

    def test_status_500_is_retryable(self):
        """500 Internal Server Error is retryable."""
        exc = type("HTTPException", (Exception,), {"status_code": 500})()
        assert is_retryable_error(exc) is True

    def test_status_502_is_retryable(self):
        """502 Bad Gateway is retryable."""
        exc = type("HTTPException", (Exception,), {"status_code": 502})()
        assert is_retryable_error(exc) is True

    def test_status_503_is_retryable(self):
        """503 Service Unavailable is retryable."""
        exc = type("HTTPException", (Exception,), {"status_code": 503})()
        assert is_retryable_error(exc) is True

    def test_status_504_is_retryable(self):
        """504 Gateway Timeout is retryable."""
        exc = type("HTTPException", (Exception,), {"status_code": 504})()
        assert is_retryable_error(exc) is True

    def test_status_599_is_retryable(self):
        """599 is retryable (5xx range)."""
        exc = type("HTTPException", (Exception,), {"status_code": 599})()
        assert is_retryable_error(exc) is True

    # --- Status codes: 4xx (except 429) are NOT retryable ---

    def test_status_400_is_not_retryable(self):
        """400 Bad Request is not retryable."""
        exc = type("HTTPException", (Exception,), {"status_code": 400})()
        assert is_retryable_error(exc) is False

    def test_status_401_is_not_retryable(self):
        """401 Unauthorized is not retryable."""
        exc = type("HTTPException", (Exception,), {"status_code": 401})()
        assert is_retryable_error(exc) is False

    def test_status_403_is_not_retryable(self):
        """403 Forbidden is not retryable."""
        exc = type("HTTPException", (Exception,), {"status_code": 403})()
        assert is_retryable_error(exc) is False

    def test_status_404_is_not_retryable(self):
        """404 Not Found is not retryable."""
        exc = type("HTTPException", (Exception,), {"status_code": 404})()
        assert is_retryable_error(exc) is False

    def test_status_422_is_not_retryable(self):
        """422 Unprocessable Entity is not retryable."""
        exc = type("HTTPException", (Exception,), {"status_code": 422})()
        assert is_retryable_error(exc) is False

    # --- Status codes: 3xx are NOT retryable ---

    def test_status_300_is_not_retryable(self):
        """3xx status codes are not retryable."""
        exc = type("HTTPException", (Exception,), {"status_code": 300})()
        assert is_retryable_error(exc) is False

    def test_status_301_is_not_retryable(self):
        """301 is not retryable."""
        exc = type("HTTPException", (Exception,), {"status_code": 301})()
        assert is_retryable_error(exc) is False

    # --- Status codes: 2xx are NOT retryable ---

    def test_status_200_is_not_retryable(self):
        """200 OK should not be retryable."""
        exc = type("HTTPException", (Exception,), {"status_code": 200})()
        assert is_retryable_error(exc) is False

    # --- Non-status exceptions are NOT retryable ---

    def test_generic_exception_is_not_retryable(self):
        """A generic exception with no status code is not retryable."""
        exc = ValueError("Some error")
        assert is_retryable_error(exc) is False

    def test_exception_with_non_int_status_code_is_not_retryable(self):
        """Exception with string status_code is not retryable."""
        exc = type("HTTPException", (Exception,), {"status_code": "500"})()
        assert is_retryable_error(exc) is False

    def test_exception_with_none_status_code_is_not_retryable(self):
        """Exception with status_code=None is not retryable."""
        exc = type("HTTPException", (Exception,), {"status_code": None})()
        assert is_retryable_error(exc) is False

    def test_exception_with_no_status_or_code_is_not_retryable(self):
        """Exception with no status_code or code attribute is not retryable."""
        exc = RuntimeError("Some runtime error")
        assert is_retryable_error(exc) is False

    # --- Edge cases ---

    def test_exception_with_code_attribute_instead_of_status_code(self):
        """Falls back to 'code' attribute if status_code is missing."""
        exc = type("CustomException", (Exception,), {"code": 503})()
        assert is_retryable_error(exc) is True

    def test_exception_with_code_401_is_not_retryable(self):
        """4xx status via 'code' attribute is not retryable."""
        exc = type("CustomException", (Exception,), {"code": 401})()
        assert is_retryable_error(exc) is False

    def test_exception_with_both_status_code_and_code_prefers_status_code(self):
        """Prefers status_code over code if both present."""
        exc = type("CustomException", (Exception,), {
            "status_code": 500,
            "code": 400,
        })()
        assert is_retryable_error(exc) is True

    def test_exception_with_string_code_fallback(self):
        """String code attribute is not treated as status."""
        exc = type("CustomException", (Exception,), {"code": "500"})()
        assert is_retryable_error(exc) is False

    def test_combined_httpx_request_error_subclass(self):
        """Subclass of httpx.RequestError is retryable."""
        exc = httpx.ConnectError("Connection failed")
        assert is_retryable_error(exc) is True
