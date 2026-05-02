from unittest.mock import MagicMock, Mock
import pytest

from app.utils.token_logging import (
    _safe_int,
    _extract_anthropic,
    _extract_openai,
    _extract_gemini,
    log_token_usage,
)


class TestSafeInt:
    """Test _safe_int() for safe integer conversion."""

    def test_converts_int_value(self):
        """Integer should return as-is."""
        assert _safe_int(42) == 42

    def test_converts_string_int(self):
        """String integer should be converted."""
        assert _safe_int("42") == 42

    def test_converts_float(self):
        """Float should be converted to int."""
        assert _safe_int(3.14) == 3

    def test_converts_string_float_raises_value_error(self):
        """String float cannot be converted directly by int() and returns 0."""
        assert _safe_int("3.14") == 0

    def test_none_returns_zero(self):
        """None should return 0."""
        assert _safe_int(None) == 0

    def test_invalid_string_returns_zero(self):
        """Invalid string should return 0."""
        assert _safe_int("not a number") == 0

    def test_list_returns_zero(self):
        """List should return 0 (TypeError)."""
        assert _safe_int([1, 2, 3]) == 0

    def test_dict_returns_zero(self):
        """Dict should return 0 (TypeError)."""
        assert _safe_int({"value": 42}) == 0

    def test_zero_returns_zero(self):
        """Zero should return 0."""
        assert _safe_int(0) == 0

    def test_negative_number_returns_negative(self):
        """Negative number should work."""
        assert _safe_int(-42) == -42


class TestExtractAnthropic:
    """Test _extract_anthropic() for Anthropic SDK response parsing."""

    def test_no_usage_attribute_returns_empty_dict(self):
        """Response without usage should return empty dict."""
        response = MagicMock()
        delattr(response, "usage")
        result = _extract_anthropic(response)
        assert result == {}

    def test_usage_is_none_returns_empty_dict(self):
        """Response with usage=None should return empty dict."""
        response = MagicMock()
        response.usage = None
        result = _extract_anthropic(response)
        assert result == {}

    def test_basic_usage_extraction(self):
        """Basic usage fields should extract correctly."""
        response = MagicMock()
        response.usage.input_tokens = 100
        response.usage.output_tokens = 50
        response.usage.cache_read_input_tokens = 0
        response.usage.cache_creation_input_tokens = 0
        result = _extract_anthropic(response)
        assert result == {
            "input": 100,
            "output": 50,
            "cache_read": 0,
            "cache_write": 0,
        }

    def test_usage_with_cache_fields(self):
        """Cache fields should extract correctly."""
        response = MagicMock()
        response.usage.input_tokens = 100
        response.usage.output_tokens = 50
        response.usage.cache_read_input_tokens = 25
        response.usage.cache_creation_input_tokens = 10
        result = _extract_anthropic(response)
        assert result == {
            "input": 100,
            "output": 50,
            "cache_read": 25,
            "cache_write": 10,
        }

    def test_usage_missing_fields_default_to_zero(self):
        """Missing fields should default to 0."""
        response = MagicMock()
        usage = MagicMock()
        usage.input_tokens = 100
        usage.output_tokens = 50
        # Simulate missing cache fields
        delattr(usage, "cache_read_input_tokens")
        delattr(usage, "cache_creation_input_tokens")
        response.usage = usage
        result = _extract_anthropic(response)
        assert result == {
            "input": 100,
            "output": 50,
            "cache_read": 0,
            "cache_write": 0,
        }

    def test_usage_with_none_fields(self):
        """None fields should convert to 0."""
        response = MagicMock()
        response.usage.input_tokens = None
        response.usage.output_tokens = None
        response.usage.cache_read_input_tokens = None
        response.usage.cache_creation_input_tokens = None
        result = _extract_anthropic(response)
        assert result == {
            "input": 0,
            "output": 0,
            "cache_read": 0,
            "cache_write": 0,
        }

    def test_usage_with_invalid_types(self):
        """Invalid types should convert to 0."""
        response = MagicMock()
        response.usage.input_tokens = "not a number"
        response.usage.output_tokens = {"value": 50}
        response.usage.cache_read_input_tokens = [1, 2, 3]
        response.usage.cache_creation_input_tokens = None
        result = _extract_anthropic(response)
        assert result == {
            "input": 0,
            "output": 0,
            "cache_read": 0,
            "cache_write": 0,
        }


class TestExtractOpenAI:
    """Test _extract_openai() for OpenAI SDK response parsing."""

    def test_no_usage_attribute_returns_empty_dict(self):
        """Response without usage should return empty dict."""
        response = MagicMock()
        delattr(response, "usage")
        result = _extract_openai(response)
        assert result == {}

    def test_usage_is_none_returns_empty_dict(self):
        """Response with usage=None should return empty dict."""
        response = MagicMock()
        response.usage = None
        result = _extract_openai(response)
        assert result == {}

    def test_basic_usage_extraction(self):
        """Basic usage fields should extract correctly."""
        response = MagicMock()
        response.usage.prompt_tokens = 100
        response.usage.completion_tokens = 50
        response.usage.prompt_tokens_details = None
        result = _extract_openai(response)
        assert result == {
            "input": 100,
            "output": 50,
            "cache_read": 0,
            "cache_write": 0,
        }

    def test_usage_with_prompt_tokens_details(self):
        """Cache tokens from prompt_tokens_details should extract."""
        response = MagicMock()
        response.usage.prompt_tokens = 100
        response.usage.completion_tokens = 50
        response.usage.prompt_tokens_details.cached_tokens = 25
        result = _extract_openai(response)
        assert result == {
            "input": 100,
            "output": 50,
            "cache_read": 25,
            "cache_write": 0,
        }

    def test_usage_with_prompt_tokens_details_none(self):
        """When prompt_tokens_details is None, cache_read should be 0."""
        response = MagicMock()
        response.usage.prompt_tokens = 100
        response.usage.completion_tokens = 50
        response.usage.prompt_tokens_details = None
        result = _extract_openai(response)
        assert result["cache_read"] == 0

    def test_usage_missing_cached_tokens_field(self):
        """Missing cached_tokens field should default to 0."""
        response = MagicMock()
        response.usage.prompt_tokens = 100
        response.usage.completion_tokens = 50
        details = MagicMock()
        delattr(details, "cached_tokens")
        response.usage.prompt_tokens_details = details
        result = _extract_openai(response)
        assert result["cache_read"] == 0

    def test_usage_with_none_prompt_tokens(self):
        """None prompt_tokens should convert to 0."""
        response = MagicMock()
        response.usage.prompt_tokens = None
        response.usage.completion_tokens = None
        response.usage.prompt_tokens_details = None
        result = _extract_openai(response)
        assert result == {
            "input": 0,
            "output": 0,
            "cache_read": 0,
            "cache_write": 0,
        }

    def test_usage_with_invalid_token_values(self):
        """Invalid token values should convert to 0."""
        response = MagicMock()
        response.usage.prompt_tokens = "invalid"
        response.usage.completion_tokens = [1, 2, 3]
        response.usage.prompt_tokens_details = None
        result = _extract_openai(response)
        assert result["input"] == 0
        assert result["output"] == 0


class TestExtractGemini:
    """Test _extract_gemini() for Gemini SDK response parsing."""

    def test_no_usage_metadata_attribute_returns_empty_dict(self):
        """Response without usage_metadata should return empty dict."""
        response = MagicMock()
        delattr(response, "usage_metadata")
        result = _extract_gemini(response)
        assert result == {}

    def test_usage_metadata_is_none_returns_empty_dict(self):
        """Response with usage_metadata=None should return empty dict."""
        response = MagicMock()
        response.usage_metadata = None
        result = _extract_gemini(response)
        assert result == {}

    def test_basic_usage_metadata_extraction(self):
        """Basic usage_metadata fields should extract correctly."""
        response = MagicMock()
        response.usage_metadata.prompt_token_count = 100
        response.usage_metadata.candidates_token_count = 50
        response.usage_metadata.cached_content_token_count = 0
        result = _extract_gemini(response)
        assert result == {
            "input": 100,
            "output": 50,
            "cache_read": 0,
            "cache_write": 0,
        }

    def test_usage_metadata_with_cached_content_tokens(self):
        """Cached content tokens should extract correctly."""
        response = MagicMock()
        response.usage_metadata.prompt_token_count = 100
        response.usage_metadata.candidates_token_count = 50
        response.usage_metadata.cached_content_token_count = 25
        result = _extract_gemini(response)
        assert result == {
            "input": 100,
            "output": 50,
            "cache_read": 25,
            "cache_write": 0,
        }

    def test_usage_metadata_missing_cached_content_tokens(self):
        """Missing cached_content_token_count should default to 0."""
        response = MagicMock()
        response.usage_metadata.prompt_token_count = 100
        response.usage_metadata.candidates_token_count = 50
        delattr(response.usage_metadata, "cached_content_token_count")
        result = _extract_gemini(response)
        assert result["cache_read"] == 0

    def test_usage_metadata_with_none_values(self):
        """None values should convert to 0."""
        response = MagicMock()
        response.usage_metadata.prompt_token_count = None
        response.usage_metadata.candidates_token_count = None
        response.usage_metadata.cached_content_token_count = None
        result = _extract_gemini(response)
        assert result == {
            "input": 0,
            "output": 0,
            "cache_read": 0,
            "cache_write": 0,
        }

    def test_usage_metadata_with_invalid_types(self):
        """Invalid types should convert to 0."""
        response = MagicMock()
        response.usage_metadata.prompt_token_count = "invalid"
        response.usage_metadata.candidates_token_count = {"value": 50}
        response.usage_metadata.cached_content_token_count = [1, 2, 3]
        result = _extract_gemini(response)
        assert result == {
            "input": 0,
            "output": 0,
            "cache_read": 0,
            "cache_write": 0,
        }


class TestLogTokenUsage:
    """Test log_token_usage() for logging across providers."""

    def test_anthropic_provider_logs_usage(self):
        """Anthropic provider should log usage correctly."""
        logger = MagicMock()
        response = MagicMock()
        response.usage.input_tokens = 100
        response.usage.output_tokens = 50
        response.usage.cache_read_input_tokens = 10
        response.usage.cache_creation_input_tokens = 5

        log_token_usage(
            logger,
            provider="anthropic",
            operation="generate_story",
            model="claude-3-5-sonnet-20241022",
            response=response,
        )

        logger.info.assert_called_once()
        args = logger.info.call_args[0]
        assert "TOKEN_USAGE" in args[0]
        assert "anthropic" in args
        assert "generate_story" in args

    def test_openai_provider_logs_usage(self):
        """OpenAI provider should log usage correctly."""
        logger = MagicMock()
        response = MagicMock()
        response.usage.prompt_tokens = 100
        response.usage.completion_tokens = 50
        response.usage.prompt_tokens_details = None

        log_token_usage(
            logger,
            provider="openai",
            operation="generate_story",
            model="gpt-4o-mini",
            response=response,
        )

        logger.info.assert_called_once()
        args = logger.info.call_args[0]
        assert "TOKEN_USAGE" in args[0]
        assert "openai" in args

    def test_groq_provider_logs_usage(self):
        """Groq provider (OpenAI-compatible) should log usage."""
        logger = MagicMock()
        response = MagicMock()
        response.usage.prompt_tokens = 80
        response.usage.completion_tokens = 40
        response.usage.prompt_tokens_details = None

        log_token_usage(
            logger,
            provider="groq",
            operation="analyze",
            model="llama-3.1-70b-versatile",
            response=response,
        )

        logger.info.assert_called_once()
        args = logger.info.call_args[0]
        assert "groq" in args

    def test_gemini_provider_logs_usage(self):
        """Gemini provider should log usage correctly."""
        logger = MagicMock()
        response = MagicMock()
        response.usage_metadata.prompt_token_count = 100
        response.usage_metadata.candidates_token_count = 50
        response.usage_metadata.cached_content_token_count = 0

        log_token_usage(
            logger,
            provider="gemini",
            operation="generate_story",
            model="gemini-2.0-flash",
            response=response,
        )

        logger.info.assert_called_once()
        args = logger.info.call_args[0]
        assert "TOKEN_USAGE" in args[0]
        assert "gemini" in args

    def test_unknown_provider_returns_without_logging(self):
        """Unknown provider should return early without logging."""
        logger = MagicMock()
        response = MagicMock()

        log_token_usage(
            logger,
            provider="unknown_provider",
            operation="test",
            model="some-model",
            response=response,
        )

        logger.info.assert_not_called()
        logger.debug.assert_not_called()

    def test_empty_usage_logs_debug_unavailable(self):
        """Empty usage dict should log debug message."""
        logger = MagicMock()
        response = MagicMock()
        response.usage = None

        log_token_usage(
            logger,
            provider="anthropic",
            operation="test",
            model="claude-3-5-sonnet-20241022",
            response=response,
        )

        logger.debug.assert_called_once()
        args = logger.debug.call_args[0]
        assert "TOKEN_USAGE" in args[0]
        assert "usage=unavailable" in args[0]

    def test_exception_in_logger_doesnt_break_function(self):
        """Function should handle exceptions in logger calls gracefully."""
        logger = MagicMock()
        logger.info.side_effect = RuntimeError("Logger broken")
        response = MagicMock()
        response.usage.input_tokens = 100
        response.usage.output_tokens = 50
        response.usage.cache_read_input_tokens = 0
        response.usage.cache_creation_input_tokens = 0

        # This should not raise even though logger.info raises
        log_token_usage(
            logger,
            provider="anthropic",
            operation="test",
            model="claude-3-5-sonnet-20241022",
            response=response,
        )
        # If we got here without an exception, the test passes

    def test_anthropic_with_cache_fields_logs_correct_values(self):
        """Anthropic response with cache should log all fields."""
        logger = MagicMock()
        response = MagicMock()
        response.usage.input_tokens = 100
        response.usage.output_tokens = 50
        response.usage.cache_read_input_tokens = 20
        response.usage.cache_creation_input_tokens = 15

        log_token_usage(
            logger,
            provider="anthropic",
            operation="generate",
            model="claude-3-5-sonnet-20241022",
            response=response,
        )

        logger.info.assert_called_once()
        call_args = logger.info.call_args[0]
        # Verify the format string and values
        assert call_args[1] == "anthropic"  # provider
        assert call_args[2] == "generate"   # operation

    def test_openai_with_cached_tokens_logs_correctly(self):
        """OpenAI response with cached_tokens should log cache_read."""
        logger = MagicMock()
        response = MagicMock()
        response.usage.prompt_tokens = 100
        response.usage.completion_tokens = 50
        response.usage.prompt_tokens_details.cached_tokens = 30

        log_token_usage(
            logger,
            provider="openai",
            operation="generate",
            model="gpt-4o-mini",
            response=response,
        )

        logger.info.assert_called_once()
        call_args = logger.info.call_args[0]
        # Cache_read should be 30
        assert call_args[6] == 30  # cache_read position

    def test_gemini_with_cached_content_logs_correctly(self):
        """Gemini response with cached_content should log cache_read."""
        logger = MagicMock()
        response = MagicMock()
        response.usage_metadata.prompt_token_count = 100
        response.usage_metadata.candidates_token_count = 50
        response.usage_metadata.cached_content_token_count = 25

        log_token_usage(
            logger,
            provider="gemini",
            operation="analyze",
            model="gemini-2.0-flash",
            response=response,
        )

        logger.info.assert_called_once()
        call_args = logger.info.call_args[0]
        # Cache_read should be 25
        assert call_args[6] == 25  # cache_read position

    def test_log_message_format_structure(self):
        """Log message should have correct TOKEN_USAGE format."""
        logger = MagicMock()
        response = MagicMock()
        response.usage.input_tokens = 100
        response.usage.output_tokens = 50
        response.usage.cache_read_input_tokens = 10
        response.usage.cache_creation_input_tokens = 5

        log_token_usage(
            logger,
            provider="anthropic",
            operation="test_op",
            model="test-model",
            response=response,
        )

        logger.info.assert_called_once()
        format_string = logger.info.call_args[0][0]
        # Verify format string contains expected fields
        assert "TOKEN_USAGE" in format_string
        assert "provider=" in format_string
        assert "op=" in format_string
        assert "model=" in format_string
        assert "input=" in format_string
        assert "output=" in format_string
        assert "cache_read=" in format_string
        assert "cache_write=" in format_string

    def test_multiple_providers_sequence(self):
        """Multiple providers should log independently."""
        logger = MagicMock()

        # Log Anthropic
        response_ant = MagicMock()
        response_ant.usage.input_tokens = 100
        response_ant.usage.output_tokens = 50
        response_ant.usage.cache_read_input_tokens = 0
        response_ant.usage.cache_creation_input_tokens = 0
        log_token_usage(logger, provider="anthropic", operation="test", model="m1", response=response_ant)

        # Log OpenAI
        response_oai = MagicMock()
        response_oai.usage.prompt_tokens = 80
        response_oai.usage.completion_tokens = 40
        response_oai.usage.prompt_tokens_details = None
        log_token_usage(logger, provider="openai", operation="test", model="m2", response=response_oai)

        assert logger.info.call_count == 2
