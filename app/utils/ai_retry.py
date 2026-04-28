import httpx

# Class names from anthropic and openai SDKs that indicate transient failures.
# Matched by name to avoid hard import dependencies on either SDK.
_RETRYABLE_EXC_NAMES = frozenset({
    "APIConnectionError",
    "APITimeoutError",
    "RateLimitError",
    "InternalServerError",
    "ServiceUnavailableError",
})


def is_retryable_error(exc: Exception) -> bool:
    """Decide whether an exception from an AI provider should trigger a retry.

    Retry only on transient failures (network, timeout, rate limit, 5xx).
    Deterministic errors (parse failures, shape validation, 4xx) fail fast — a
    second call with the same prompt and temperature=0 will produce the same
    result and only burn tokens.
    """
    if isinstance(exc, (httpx.RequestError, TimeoutError, ConnectionError)):
        return True

    if type(exc).__name__ in _RETRYABLE_EXC_NAMES:
        return True

    status = getattr(exc, "status_code", None)
    if not isinstance(status, int):
        status = getattr(exc, "code", None)
    if isinstance(status, int):
        if status == 429 or status >= 500:
            return True
        if 400 <= status < 500:
            return False

    return False
