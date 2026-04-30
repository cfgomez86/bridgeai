import re

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.services.story_ai_provider import StoryAIProvider
from app.utils.ai_retry import is_retryable_error

_REQUIRED_FIELDS = {
    "title", "story_description", "acceptance_criteria", "subtasks",
}
# Soft fields: filled with [] when absent so the story still passes through.
# Their quality (or lack thereof) is reflected in structural metrics + judge scoring.
_OPTIONAL_LIST_FIELDS = ("definition_of_done", "risk_notes")
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
_MAX_TITLE_LEN = 150
_MIN_DESCRIPTION_LEN = 30

# Acceptance criteria must follow Given/When/Then. Match across the main supported languages.
_GWT_PATTERNS = [
    re.compile(r"\bdado\b.*\bcuando\b.*\bentonces\b", re.IGNORECASE | re.DOTALL),
    re.compile(r"\bgiven\b.*\bwhen\b.*\bthen\b", re.IGNORECASE | re.DOTALL),
    re.compile(r"\bdado\b.*\bquando\b.*\bent[aã]o\b", re.IGNORECASE | re.DOTALL),
    re.compile(r"\b(?:étant donné|etant donne)\b.*\b(?:quand|lorsque)\b.*\balors\b", re.IGNORECASE | re.DOTALL),
    re.compile(r"\b(?:angenommen|gegeben)\b.*\bwenn\b.*\bdann\b", re.IGNORECASE | re.DOTALL),
]
_GWT_MIN_RATIO = 0.6

# Conservative UI signals — only trigger when the story clearly touches an interface.
# Pure backend / job / cron / migration stories must NOT match here so that
# subtasks.frontend remains a legitimate empty array.
_UI_KEYWORD_PATTERN = re.compile(
    r"\b(?:"
    r"formulario|formularios|form|forms|"
    r"pantalla|pantallas|screen|screens|"
    r"dashboard|dashboards|"
    r"modal|modales|modals|"
    r"ui|interfaz|"
    r"register|signup|registro|registrarse|registrar|login|"
    r"p[aá]gina|p[aá]ginas|page|pages"
    r")\b",
    re.IGNORECASE,
)


class HallucinatedPathError(ValueError):
    """Raised when the AI cites file paths that don't exist in the whitelist."""

    def __init__(self, invalid_paths: list[str]) -> None:
        super().__init__(
            f"Response references paths outside the whitelist: {invalid_paths}"
        )
        self.invalid_paths = invalid_paths


class StoryQualityRetryError(ValueError):
    """Raised when the response is shape-valid but breaks a quality rule
    (AC not in Given/When/Then, missing frontend on a UI story, etc.)."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class TransientGenerationError(Exception):
    """All retries exhausted on transient upstream failures (timeout, 5xx,
    network). Surfaces as 504 Gateway Timeout — not a client (4xx) error."""

    def __init__(self, attempts: int, last_error: Exception) -> None:
        super().__init__(
            f"Story generation failed after {attempts} transient errors: {last_error}"
        )
        self.attempts = attempts
        self.last_error = last_error


class AIStoryGenerator:
    def __init__(self, provider: StoryAIProvider, settings: Settings = None) -> None:
        self._provider = provider
        self._max_retries = (settings or get_settings()).AI_MAX_RETRIES
        self._logger = get_logger(__name__)

    @property
    def model_name(self) -> str:
        return self._provider.model_name

    def generate(self, context: dict) -> dict:
        last_error: Exception | None = None
        attempt_context = dict(context)
        whitelist = set(context.get("available_file_paths") or [])
        last_validated: dict | None = None

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
                last_validated = validated
                self._check_ac_format(validated["acceptance_criteria"])
                self._check_frontend_explicit(validated, context)
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
            except StoryQualityRetryError as exc:
                last_error = exc
                self._logger.warning(
                    "Attempt %d/%d failed quality check: %s",
                    attempt + 1, self._max_retries + 1, exc.reason,
                )
                if attempt < self._max_retries:
                    attempt_context = dict(context)
                    attempt_context["quality_warning_reason"] = exc.reason
                    continue
                self._logger.warning(
                    "Max retries reached on quality check; returning best-effort response"
                )
                return last_validated  # shape-valid even if quality is suboptimal
            except Exception as exc:
                last_error = exc
                if not is_retryable_error(exc):
                    self._logger.warning(
                        "Non-retryable error from story AI provider: %s", exc,
                    )
                    raise
                self._logger.warning(
                    "Attempt %d/%d failed (transient): %s",
                    attempt + 1, self._max_retries + 1, exc,
                )
                if attempt < self._max_retries:
                    continue
        raise TransientGenerationError(self._max_retries + 1, last_error)

    @staticmethod
    def _ac_uses_gwt(text: str) -> bool:
        if not isinstance(text, str):
            return False
        return any(p.search(text) for p in _GWT_PATTERNS)

    def _check_ac_format(self, criteria: list) -> None:
        if not criteria:
            return  # absence already caught by _validate_shape
        matches = sum(1 for c in criteria if self._ac_uses_gwt(c))
        ratio = matches / len(criteria)
        if ratio < _GWT_MIN_RATIO:
            raise StoryQualityRetryError(
                "los criterios de aceptación no siguen el formato Given/When/Then verificable "
                f"(solo {matches} de {len(criteria)} cumplen). Reescribe TODOS los AC en el patrón "
                "'Dado <contexto>, Cuando <acción>, Entonces <resultado medible>' "
                "(o 'Given/When/Then' en inglés) con resultados concretos y comprobables."
            )

    @staticmethod
    def _context_implies_ui(context: dict) -> bool:
        keywords = context.get("keywords") or []
        if not isinstance(keywords, list):
            keywords = []
        parts = [
            str(context.get("requirement_text", "")),
            str(context.get("intent", "")),
            str(context.get("feature_type", "")),
            " ".join(str(k) for k in keywords),
        ]
        text = " ".join(parts)
        return bool(_UI_KEYWORD_PATTERN.search(text))

    def _check_frontend_explicit(self, raw: dict, context: dict) -> None:
        """Only fire the retry when the context clearly implies UI AND frontend is empty.

        If the story is genuinely backend-only (no UI keywords in requirement/intent/keywords),
        an empty `frontend` is left untouched per design.
        """
        if not self._context_implies_ui(context):
            return
        frontend = raw.get("subtasks", {}).get("frontend") or []
        if frontend:
            return
        raise StoryQualityRetryError(
            "la historia involucra interfaz de usuario (formulario / pantalla / dashboard según el "
            "contexto) pero subtasks.frontend está vacío. Genera al menos 2 tareas frontend que "
            "cubran (1) estructura del componente o pantalla, (2) validaciones / estados de UI / "
            "mensajes de error y (3) integración con la API. Si no hay archivos UI en el whitelist, "
            "describe el componente NUEVO a crear sin inventar paths concretos."
        )

    def _validate_shape(self, raw: dict) -> dict:
        missing = _REQUIRED_FIELDS - raw.keys()
        if missing:
            raise ValueError(f"Story response missing required fields: {missing}")
        for field in _OPTIONAL_LIST_FIELDS:
            if field not in raw or raw[field] is None:
                self._logger.warning(
                    "AI response missing optional field %r; defaulting to []", field
                )
                raw[field] = []
            elif not isinstance(raw[field], list):
                raise ValueError(f"{field} must be a list")
        if not str(raw["title"]).strip():
            raise ValueError("title cannot be empty")
        if not str(raw["story_description"]).strip():
            raise ValueError("story_description cannot be empty")
        if not isinstance(raw["acceptance_criteria"], list) or len(raw["acceptance_criteria"]) == 0:
            raise ValueError("acceptance_criteria must be a non-empty list")
        subtasks = raw.get("subtasks")
        if not isinstance(subtasks, dict):
            raise ValueError("subtasks must be an object")
        for cat in _SUBTASK_CATEGORIES:
            if cat not in subtasks:
                subtasks[cat] = []
            if not isinstance(subtasks[cat], list):
                raise ValueError(f"subtasks.{cat} must be a list")
            for idx, item in enumerate(subtasks[cat]):
                if not isinstance(item, dict):
                    raise ValueError(
                        f"subtasks.{cat}[{idx}] must be an object with 'title' and 'description'"
                    )
                title = str(item.get("title", "")).strip()
                description = str(item.get("description", "")).strip()
                if not title:
                    raise ValueError(f"subtasks.{cat}[{idx}].title cannot be empty")
                if len(title) < _MIN_SUBTASK_LEN:
                    raise ValueError(
                        f"subtasks.{cat}[{idx}].title must be at least {_MIN_SUBTASK_LEN} characters"
                    )
                if len(title) > _MAX_TITLE_LEN:
                    raise ValueError(
                        f"subtasks.{cat}[{idx}].title must be at most {_MAX_TITLE_LEN} characters"
                    )
                if not description:
                    raise ValueError(
                        f"subtasks.{cat}[{idx}].description cannot be empty"
                    )
                if len(description) < _MIN_DESCRIPTION_LEN:
                    raise ValueError(
                        f"subtasks.{cat}[{idx}].description must be at least {_MIN_DESCRIPTION_LEN} characters"
                    )
                item["title"] = title
                item["description"] = description
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
                if isinstance(item, dict):
                    combined = f"{item.get('title', '')}\n{item.get('description', '')}"
                else:
                    combined = item if isinstance(item, str) else ""
                for path in self._extract_paths(combined):
                    if path not in whitelist and path not in invalid:
                        invalid.append(path)
        for item in raw.get("risk_notes", []):
            for path in self._extract_paths(item):
                if path not in whitelist and path not in invalid:
                    invalid.append(path)
        return invalid

    def _strip_invalid_paths(self, raw: dict, whitelist: set[str]) -> dict:
        def _clean_inline(text: str) -> str:
            """Para titles y risk_notes: limpia paths inválidos y colapsa whitespace."""
            if not isinstance(text, str):
                return text
            for path in self._extract_paths(text):
                if path in whitelist:
                    continue
                text = self._remove_path_phrase(text, path)
            return re.sub(r"\s+", " ", text).strip(" .,;:")

        def _clean_multiline(text: str) -> str:
            """Para descriptions: limpia paths inválidos preservando saltos de línea."""
            if not isinstance(text, str):
                return text
            for path in self._extract_paths(text):
                if path in whitelist:
                    continue
                text = self._remove_path_phrase(text, path)
            # Colapsa solo espacios/tabs sin tocar \n; recorta espacios laterales por línea
            lines = [re.sub(r"[ \t]+", " ", ln).strip(" .,;:") for ln in text.split("\n")]
            return "\n".join(lines).strip()

        out = dict(raw)
        subtasks = dict(raw.get("subtasks", {}))
        for cat in _SUBTASK_CATEGORIES:
            cleaned: list[dict] = []
            for item in subtasks.get(cat, []):
                if not isinstance(item, dict):
                    continue
                new_title = _clean_inline(str(item.get("title", "")))
                new_description = _clean_multiline(str(item.get("description", "")))
                if new_title and len(new_title) >= _MIN_SUBTASK_LEN and new_description:
                    cleaned.append({"title": new_title, "description": new_description})
            subtasks[cat] = cleaned
        if not any(subtasks[c] for c in _SUBTASK_CATEGORIES):
            subtasks["backend"] = [
                {
                    "title": "Revisar el codebase indexado y definir tareas concretas",
                    "description": "No hubo archivos verificables para referenciar en el whitelist. Inspeccionar el repo y descomponer la historia en tareas accionables manualmente.",
                }
            ]
        out["subtasks"] = subtasks
        out["risk_notes"] = [_clean_inline(n) for n in raw.get("risk_notes", []) if _clean_inline(n)]
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
