"""Uniform token-usage logging across Anthropic / OpenAI-compatible / Gemini SDKs.

Each SDK exposes usage on a different attribute path. This module normalises the
extraction so a single grep on `TOKEN_USAGE` returns a consistent line shape:

    TOKEN_USAGE provider=<p> op=<op> model=<m> input=<n> output=<n> cache_read=<n> cache_write=<n>

`cache_read` and `cache_write` are 0 when the provider does not report them.
Failures to read usage never raise — they downgrade to a debug log so an SDK
shape change can never break the request path.
"""

from typing import Any


def _safe_int(value: Any) -> int:
    try:
        return int(value) if value is not None else 0
    except (TypeError, ValueError):
        return 0


def _extract_anthropic(response: Any) -> dict:
    usage = getattr(response, "usage", None)
    if usage is None:
        return {}
    return {
        "input": _safe_int(getattr(usage, "input_tokens", 0)),
        "output": _safe_int(getattr(usage, "output_tokens", 0)),
        "cache_read": _safe_int(getattr(usage, "cache_read_input_tokens", 0)),
        "cache_write": _safe_int(getattr(usage, "cache_creation_input_tokens", 0)),
    }


def _extract_openai(response: Any) -> dict:
    usage = getattr(response, "usage", None)
    if usage is None:
        return {}
    cached = 0
    details = getattr(usage, "prompt_tokens_details", None)
    if details is not None:
        cached = _safe_int(getattr(details, "cached_tokens", 0))
    return {
        "input": _safe_int(getattr(usage, "prompt_tokens", 0)),
        "output": _safe_int(getattr(usage, "completion_tokens", 0)),
        "cache_read": cached,
        "cache_write": 0,
    }


def _extract_gemini(response: Any) -> dict:
    meta = getattr(response, "usage_metadata", None)
    if meta is None:
        return {}
    return {
        "input": _safe_int(getattr(meta, "prompt_token_count", 0)),
        "output": _safe_int(getattr(meta, "candidates_token_count", 0)),
        "cache_read": _safe_int(getattr(meta, "cached_content_token_count", 0)),
        "cache_write": 0,
    }


_EXTRACTORS = {
    "anthropic": _extract_anthropic,
    "openai": _extract_openai,
    "groq": _extract_openai,  # OpenAI-compatible
    "gemini": _extract_gemini,
}


def log_token_usage(logger, *, provider: str, operation: str, model: str, response: Any) -> None:
    """Emit a single-line `TOKEN_USAGE` log entry for the given response.

    Never raises. If extraction fails, falls back to a debug log so the caller
    is never blocked by observability code.
    """
    try:
        extractor = _EXTRACTORS.get(provider)
        if extractor is None:
            return
        usage = extractor(response)
        if not usage:
            logger.debug(
                "TOKEN_USAGE provider=%s op=%s model=%s usage=unavailable",
                provider, operation, model,
            )
            return
        logger.info(
            "TOKEN_USAGE provider=%s op=%s model=%s input=%d output=%d cache_read=%d cache_write=%d",
            provider, operation, model,
            usage.get("input", 0), usage.get("output", 0),
            usage.get("cache_read", 0), usage.get("cache_write", 0),
        )
    except Exception as exc:  # defensive — observability must never break the path
        logger.debug("TOKEN_USAGE extraction failed provider=%s op=%s err=%s", provider, operation, exc)
