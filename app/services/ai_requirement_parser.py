from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.services.ai_provider import (
    AIProvider,
    VALID_COMPLEXITIES,
    VALID_DOMAINS,
    VALID_FEATURE_TYPES,
    VALID_SCOPES,
)
from app.utils.ai_retry import is_retryable_error

_REQUIRED_FIELDS = {
    "intent", "action", "entity", "feature_type", "priority",
    "business_domain", "technical_scope", "estimated_complexity", "keywords",
}


class AIRequirementParser:
    def __init__(self, provider: AIProvider, settings: Settings = None) -> None:
        self._provider = provider
        self._max_retries = (settings or get_settings()).AI_MAX_RETRIES
        self._logger = get_logger(__name__)
        # Provider calls spent on the last parse() invocation (1 + transient retries).
        # Read this immediately after parse(); subsequent calls overwrite it.
        self.last_call_count: int = 0

    @property
    def model_name(self) -> str:
        return getattr(self._provider, "model_name", "") or ""

    def parse(self, requirement_text: str) -> dict:
        last_error: Exception | None = None
        calls = 0
        for attempt in range(self._max_retries + 1):
            try:
                self._logger.info(
                    "Calling AI provider (attempt %d/%d) for requirement: %.100s",
                    attempt + 1,
                    self._max_retries + 1,
                    requirement_text,
                )
                calls += 1
                raw = self._provider.parse_requirement(requirement_text)
                self._logger.debug("Raw AI response: %.200s", str(raw))
                validated = self._validate(raw)
                self._logger.info("Validation passed for requirement parsing")
                self.last_call_count = calls
                return validated
            except Exception as exc:
                last_error = exc
                if not is_retryable_error(exc):
                    self._logger.warning("Non-retryable error from requirement AI provider: %s", exc)
                    self.last_call_count = calls
                    raise
                self._logger.warning("Attempt %d/%d failed (transient): %s", attempt + 1, self._max_retries + 1, exc)
                if attempt < self._max_retries:
                    continue
        self.last_call_count = calls
        raise ValueError(f"AI parsing failed after {self._max_retries + 1} transient errors: {last_error}")

    def _validate(self, raw: dict) -> dict:
        missing = _REQUIRED_FIELDS - raw.keys()
        if missing:
            raise ValueError(f"AI response missing required fields: {missing}")
        if raw["feature_type"] not in VALID_FEATURE_TYPES:
            raise ValueError(f"Invalid feature_type '{raw['feature_type']}'. Must be one of {VALID_FEATURE_TYPES}")
        if raw["estimated_complexity"] not in VALID_COMPLEXITIES:
            raise ValueError(f"Invalid estimated_complexity '{raw['estimated_complexity']}'. Must be one of {VALID_COMPLEXITIES}")
        if raw["business_domain"] not in VALID_DOMAINS:
            raise ValueError(f"Invalid business_domain '{raw['business_domain']}'. Must be one of {VALID_DOMAINS}")
        if raw["technical_scope"] not in VALID_SCOPES:
            raise ValueError(f"Invalid technical_scope '{raw['technical_scope']}'. Must be one of {VALID_SCOPES}")
        if not isinstance(raw["keywords"], list):
            raise ValueError("keywords must be a list")
        return raw
