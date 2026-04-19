from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.services.story_ai_provider import StoryAIProvider

_REQUIRED_FIELDS = {
    "title", "story_description", "acceptance_criteria",
    "subtasks", "definition_of_done", "risk_notes",
}
_SUBTASK_CATEGORIES = {"frontend", "backend", "configuration"}


class AIStoryGenerator:
    def __init__(self, provider: StoryAIProvider, settings: Settings = None) -> None:
        self._provider = provider
        self._max_retries = (settings or get_settings()).AI_MAX_RETRIES
        self._logger = get_logger(__name__)

    def generate(self, context: dict) -> dict:
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                self._logger.info(
                    "Calling story AI provider (attempt %d/%d)",
                    attempt + 1,
                    self._max_retries + 1,
                )
                raw = self._provider.generate_story(context)
                self._logger.debug("Raw story response: %.200s", str(raw))
                validated = self._validate(raw)
                self._logger.info("Story validation passed")
                return validated
            except Exception as exc:
                last_error = exc
                self._logger.warning("Attempt %d/%d failed: %s", attempt + 1, self._max_retries + 1, exc)
                if attempt < self._max_retries:
                    continue
        raise ValueError(f"Story generation failed after {self._max_retries + 1} attempts: {last_error}")

    def _validate(self, raw: dict) -> dict:
        missing = _REQUIRED_FIELDS - raw.keys()
        if missing:
            raise ValueError(f"Story response missing required fields: {missing}")
        if not str(raw["title"]).strip():
            raise ValueError("title cannot be empty")
        if not str(raw["story_description"]).strip():
            raise ValueError("story_description cannot be empty")
        for field in ("acceptance_criteria", "definition_of_done"):
            if not isinstance(raw[field], list) or len(raw[field]) == 0:
                raise ValueError(f"{field} must be a non-empty list")
        if not isinstance(raw["risk_notes"], list):
            raise ValueError("risk_notes must be a list")
        subtasks = raw.get("subtasks")
        if not isinstance(subtasks, dict):
            raise ValueError("subtasks must be an object")
        for cat in _SUBTASK_CATEGORIES:
            if cat not in subtasks:
                subtasks[cat] = []
            if not isinstance(subtasks[cat], list):
                raise ValueError(f"subtasks.{cat} must be a list")
        if not any(subtasks[c] for c in _SUBTASK_CATEGORIES):
            raise ValueError("subtasks must have at least one task in any category")
        return raw
