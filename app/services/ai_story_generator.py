import re

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.services.story_ai_provider import StoryAIProvider

_REQUIRED_FIELDS = {
    "title", "story_description", "acceptance_criteria",
    "subtasks", "definition_of_done", "risk_notes",
}
_SUBTASK_CATEGORIES = {"frontend", "backend", "configuration"}

_PATH_RE = re.compile(
    r"(?<![\w/])"
    r"[\w.\-]+(?:/[\w.\-]+)+"
    r"\.(?:py|pyi|ts|tsx|js|jsx|mjs|cjs|"
    r"java|kt|kts|scala|groovy|go|rs|rb|php|cs|fs|vb|"
    r"cpp|cc|cxx|c|h|hpp|hh|hxx|m|mm|swift|"
    r"sql|yml|yaml|toml|json|xml|gradle|proto|md|sh|ps1)"
    r"\b"
)

_MIN_SUBTASK_LEN = 15


class HallucinatedPathError(ValueError):
    """Raised when the AI cites file paths that don't exist in the whitelist."""

    def __init__(self, invalid_paths: list[str]) -> None:
        super().__init__(
            f"Response references paths outside the whitelist: {invalid_paths}"
        )
        self.invalid_paths = invalid_paths


class AIStoryGenerator:
    def __init__(self, provider: StoryAIProvider, settings: Settings = None) -> None:
        self._provider = provider
        self._max_retries = (settings or get_settings()).AI_MAX_RETRIES
        self._logger = get_logger(__name__)

    def generate(self, context: dict) -> dict:
        last_error: Exception | None = None
        attempt_context = dict(context)
        whitelist = set(context.get("available_file_paths") or [])

        for attempt in range(self._max_retries + 1):
            try:
                self._logger.info(
                    "Calling story AI provider (attempt %d/%d)",
                    attempt + 1,
                    self._max_retries + 1,
                )
                raw = self._provider.generate_story(attempt_context)
                self._logger.debug("Raw story response: %.200s", str(raw))
                validated = self._validate_shape(raw)
                invalid = self._find_hallucinated_paths(validated, whitelist)
                if invalid:
                    raise HallucinatedPathError(invalid)
                self._logger.info("Story validation passed")
                return validated
            except HallucinatedPathError as exc:
                last_error = exc
                self._logger.warning(
                    "Attempt %d/%d hallucinated %d path(s): %s",
                    attempt + 1, self._max_retries + 1,
                    len(exc.invalid_paths), exc.invalid_paths,
                )
                if attempt < self._max_retries:
                    attempt_context = dict(context)
                    attempt_context["hallucinated_last_attempt"] = exc.invalid_paths
                    continue
                stripped = self._strip_invalid_paths(raw, whitelist)
                self._logger.warning(
                    "Max retries reached; stripped invalid paths from response"
                )
                return self._validate_shape(stripped)
            except Exception as exc:
                last_error = exc
                self._logger.warning(
                    "Attempt %d/%d failed: %s",
                    attempt + 1, self._max_retries + 1, exc,
                )
                if attempt < self._max_retries:
                    continue
        raise ValueError(
            f"Story generation failed after {self._max_retries + 1} attempts: {last_error}"
        )

    def _validate_shape(self, raw: dict) -> dict:
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

    @staticmethod
    def _extract_paths(text: str) -> list[str]:
        if not isinstance(text, str):
            return []
        return _PATH_RE.findall(text)

    def _find_hallucinated_paths(self, raw: dict, whitelist: set[str]) -> list[str]:
        invalid: list[str] = []
        for cat in _SUBTASK_CATEGORIES:
            for item in raw.get("subtasks", {}).get(cat, []):
                for path in self._extract_paths(item):
                    if path not in whitelist and path not in invalid:
                        invalid.append(path)
        for item in raw.get("risk_notes", []):
            for path in self._extract_paths(item):
                if path not in whitelist and path not in invalid:
                    invalid.append(path)
        return invalid

    def _strip_invalid_paths(self, raw: dict, whitelist: set[str]) -> dict:
        def _clean(text: str) -> str:
            if not isinstance(text, str):
                return text
            for path in self._extract_paths(text):
                if path in whitelist:
                    continue
                text = self._remove_path_phrase(text, path)
            return re.sub(r"\s+", " ", text).strip(" .,;:")

        out = dict(raw)
        subtasks = dict(raw.get("subtasks", {}))
        for cat in _SUBTASK_CATEGORIES:
            cleaned: list[str] = []
            for item in subtasks.get(cat, []):
                new_text = _clean(item)
                if new_text and len(new_text) >= _MIN_SUBTASK_LEN:
                    cleaned.append(new_text)
            subtasks[cat] = cleaned
        if not any(subtasks[c] for c in _SUBTASK_CATEGORIES):
            subtasks["backend"] = [
                "Revisar el codebase indexado y definir tareas concretas (no hubo archivos verificables para referenciar)"
            ]
        out["subtasks"] = subtasks
        out["risk_notes"] = [_clean(n) for n in raw.get("risk_notes", []) if _clean(n)]
        return out

    @staticmethod
    def _remove_path_phrase(text: str, path: str) -> str:
        connectors = r"(?:en|in|at|from|para|desde|de|to)"
        pattern_conn = re.compile(
            rf"\s+{connectors}\s+{re.escape(path)}(?=[\s.,;:)]|$)",
            flags=re.IGNORECASE,
        )
        new_text, n = pattern_conn.subn("", text)
        if n > 0:
            return new_text
        return text.replace(path, "").strip()
