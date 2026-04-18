import logging
from abc import ABC, abstractmethod

from app.core.config import Settings, get_settings
from app.services.dependency_analyzer import FileAnalysis
from app.utils.json_utils import extract_json

try:
    import anthropic as _anthropic_lib
except ImportError:
    _anthropic_lib = None  # type: ignore[assignment]

try:
    import openai as _openai_lib
except ImportError:
    _openai_lib = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

_FILTER_PROMPT = """\
Dado este requerimiento de software:
"{requirement}"

Evalúa la relevancia de estos archivos del codebase para implementar el requerimiento.
Score: 0-30 = no relacionado, 31-70 = posiblemente relacionado, 71-100 = directamente relacionado.

Archivos:
{file_signatures}

Responde ÚNICAMENTE con JSON válido:
{{"relevant_files": [{{"path": "...", "score": 85}}]}}

Incluye solo archivos con score >= 40. Sin texto adicional.\
"""

_BATCH_SIZE = 40


def _build_signature(path: str, fa: FileAnalysis) -> str:
    parts = [path]
    if fa.classes:
        parts.append(f"classes=[{', '.join(fa.classes[:5])}]")
    if fa.functions:
        parts.append(f"functions=[{', '.join(fa.functions[:8])}]")
    return " | ".join(parts)


def _parse_response(raw: str, candidates: set[str]) -> set[str]:
    try:
        data = extract_json(raw)
        relevant = data.get("relevant_files", [])
        return {item["path"] for item in relevant if item.get("path") in candidates}
    except Exception:
        logger.warning("SemanticImpactFilter: failed to parse LLM response, keeping all candidates")
        return candidates


class SemanticImpactFilter(ABC):
    @abstractmethod
    def filter(self, requirement: str, candidates: dict[str, FileAnalysis]) -> set[str]:
        ...

    def _run_batches(self, requirement: str, candidates: dict[str, FileAnalysis]) -> set[str]:
        if not candidates:
            return set()

        items = list(candidates.items())
        batches = [items[i : i + _BATCH_SIZE] for i in range(0, len(items), _BATCH_SIZE)]
        relevant: set[str] = set()

        for batch in batches:
            signatures = "\n".join(_build_signature(p, fa) for p, fa in batch)
            prompt = _FILTER_PROMPT.format(requirement=requirement, file_signatures=signatures)
            batch_paths = {p for p, _ in batch}
            raw = self._call_llm(prompt)
            relevant |= _parse_response(raw, batch_paths)

        logger.info(
            "SemanticImpactFilter: %d candidates → %d relevant",
            len(candidates),
            len(relevant),
        )
        return relevant

    @abstractmethod
    def _call_llm(self, prompt: str) -> str:
        ...


class PassthroughFilter(SemanticImpactFilter):
    """Used when AI_PROVIDER=stub — keeps all candidates."""

    def filter(self, requirement: str, candidates: dict[str, FileAnalysis]) -> set[str]:
        return set(candidates.keys())

    def _call_llm(self, prompt: str) -> str:
        return ""


class AnthropicSemanticFilter(SemanticImpactFilter):
    def __init__(self, settings: Settings) -> None:
        if _anthropic_lib is None:
            raise ImportError("anthropic package is required")
        self._client = _anthropic_lib.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self._model = settings.AI_MODEL or "claude-haiku-4-5-20251001"
        self._timeout = settings.AI_TIMEOUT_SECONDS

    def filter(self, requirement: str, candidates: dict[str, FileAnalysis]) -> set[str]:
        return self._run_batches(requirement, candidates)

    def _call_llm(self, prompt: str) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            temperature=0,
            timeout=self._timeout,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text


class OpenAISemanticFilter(SemanticImpactFilter):
    def __init__(self, settings: Settings) -> None:
        if _openai_lib is None:
            raise ImportError("openai package is required")
        self._client = _openai_lib.OpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = settings.AI_MODEL or "gpt-4o-mini"
        self._timeout = settings.AI_TIMEOUT_SECONDS

    def filter(self, requirement: str, candidates: dict[str, FileAnalysis]) -> set[str]:
        return self._run_batches(requirement, candidates)

    def _call_llm(self, prompt: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            temperature=0,
            timeout=self._timeout,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content


def get_semantic_filter(settings: Settings = get_settings()) -> SemanticImpactFilter:
    provider = settings.AI_PROVIDER
    if provider == "anthropic":
        return AnthropicSemanticFilter(settings)
    if provider == "openai":
        return OpenAISemanticFilter(settings)
    return PassthroughFilter()
