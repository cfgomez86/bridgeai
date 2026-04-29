"""LLM-as-Judge quality evaluator for UserStory objects."""

import logging
import statistics
from abc import ABC, abstractmethod

from app.core.config import Settings, get_settings
from app.domain.user_story import UserStory
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

_DIMENSIONS = ("completeness", "specificity", "feasibility", "risk_coverage", "language_consistency")

_JUDGE_PROMPT_TEMPLATE = """\
Eres un revisor senior de historias de usuario ágiles. Eres exigente: solo das 9-10 cuando se cumplen \
TODAS las condiciones del anclaje superior. Si dudas entre dos bandas, baja la nota.

Evalúa la siguiente historia en cinco dimensiones (0-10) usando esta rúbrica anclada:

completeness — ¿la historia cubre todo lo necesario?
  9-10: descripción + ≥3 AC verificables + DoD explícito + subtareas frontend/backend/config + notas de riesgo coherentes.
  7-8 : la mayoría de los anteriores presentes; falta uno menor.
  5-6 : AC presentes pero DoD o subtareas escasas/genéricas.
  3-4 : falta más de un bloque importante.
  0-2 : solo título y descripción, sin AC ni subtareas reales.

specificity — ¿los AC son verificables y concretos?
  9-10: TODOS los AC en formato Given/When/Then o equivalente medible (ej. "responde en <300ms", "muestra el campo X").
  7-8 : la mayoría son medibles, alguno algo ambiguo.
  5-6 : la mitad son cuantificables; el resto subjetivos.
  3-4 : la mayoría son frases genéricas sin sujeto/objeto claros.
  0-2 : AC del tipo "el sistema funcione" / "sea fácil de usar".

feasibility — ¿es implementable en un sprint normal (1-2 semanas)?
  9-10: alcance claro, story points 1-5, riesgo bajo, subtareas atomizadas.
  7-8 : alcance razonable; story points hasta 8 con riesgo medio.
  5-6 : alcance grande pero divisible; story points 8-13.
  3-4 : épica disfrazada de historia, dependencias no resueltas.
  0-2 : irrealizable como historia (cross-team, sin diseño previo).

risk_coverage — ¿las notas de riesgo abordan los riesgos técnicos relevantes?
  9-10: ≥3 riesgos técnicos concretos (seguridad, performance, datos, integraciones) con mitigación.
  7-8 : 2 riesgos técnicos concretos.
  5-6 : 1-2 riesgos genéricos sin mitigación clara.
  3-4 : notas de riesgo presentes pero superficiales o off-topic.
  0-2 : sin notas de riesgo, o solo riesgos no técnicos.

language_consistency — ¿el idioma es consistente en todos los campos?
  9-10: 100% de los campos en el mismo idioma, terminología técnica coherente.
  7-8 : un campo aislado mezcla idiomas o términos.
  5-6 : varios campos mezclan idiomas.
  3-4 : mezcla amplia, dos idiomas alternándose.
  0-2 : caos lingüístico.

Historia de usuario:
Título: {title}
Descripción: {story_description}
Criterios de aceptación: {acceptance_criteria}
Subtareas (backend): {subtasks_backend}
Definición de terminado: {definition_of_done}
Notas de riesgo: {risk_notes}
Story points: {story_points}
Nivel de riesgo: {risk_level}

Para CADA nota inferior a 7, incluye en `evidence` la cita textual (máx 120 caracteres) del AC, subtarea \
o nota de riesgo que justifica esa banda. Si la nota es ≥7, omite esa dimensión de `evidence`.

Responde ÚNICAMENTE con JSON válido, sin texto adicional:
{{
  "completeness": <0-10>,
  "specificity": <0-10>,
  "feasibility": <0-10>,
  "risk_coverage": <0-10>,
  "language_consistency": <0-10>,
  "justification": "<una o dos frases con los puntos débiles principales>",
  "evidence": {{
    "<dimension>": "<cita textual de la historia que motiva una nota baja>"
  }}
}}\
"""


def _build_prompt(story: UserStory) -> str:
    subtasks_backend = story.subtasks.get("backend", [])[:3]
    return _JUDGE_PROMPT_TEMPLATE.format(
        title=story.title,
        story_description=story.story_description[:300],
        acceptance_criteria=story.acceptance_criteria[:5],
        subtasks_backend=[t.get("title", "") if isinstance(t, dict) else t for t in subtasks_backend],
        definition_of_done=story.definition_of_done[:3],
        risk_notes=story.risk_notes[:3],
        story_points=story.story_points,
        risk_level=story.risk_level,
    )


def _clamp(value: float) -> float:
    if value < 0:
        return 0.0
    if value > 10:
        return 10.0
    return value


def _parse_scores(raw: dict) -> dict:
    """Validate and normalise one LLM JSON sample."""
    required = set(_DIMENSIONS)
    missing = required - raw.keys()
    if missing:
        raise ValueError(f"Judge response missing fields: {missing}")

    scores: dict = {}
    for dim in _DIMENSIONS:
        try:
            v = float(raw[dim])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Judge response field {dim!r} not numeric: {raw[dim]!r}") from exc
        if v < 0 or v > 10:
            logger.warning("Judge returned out-of-range %s=%s; clamping to [0,10]", dim, v)
        scores[dim] = _clamp(v)

    scores["overall"] = round(sum(scores[d] for d in _DIMENSIONS) / len(_DIMENSIONS), 2)
    scores["justification"] = str(raw.get("justification", ""))

    evidence_raw = raw.get("evidence", {})
    evidence: dict = {}
    if isinstance(evidence_raw, dict):
        for dim in _DIMENSIONS:
            cite = evidence_raw.get(dim)
            if isinstance(cite, str) and cite.strip():
                evidence[dim] = cite.strip()[:200]
    scores["evidence"] = evidence
    return scores


def _aggregate_samples(samples: list[dict]) -> dict:
    """Combine N parsed samples into a single robust score dict.

    - Per-dimension scores: median across samples (robust to outliers at N=3).
    - dispersion: population stdev of `overall` across samples (0 if N=1).
    - evidence: taken from the sample whose overall is closest to the median overall,
      so all citations come from a single coherent judgment.
    """
    if not samples:
        raise ValueError("Cannot aggregate zero samples")

    aggregated: dict = {}
    for dim in _DIMENSIONS:
        aggregated[dim] = round(statistics.median(s[dim] for s in samples), 2)

    aggregated["overall"] = round(sum(aggregated[d] for d in _DIMENSIONS) / len(_DIMENSIONS), 2)

    overalls = [s["overall"] for s in samples]
    if len(overalls) > 1:
        aggregated["dispersion"] = round(statistics.pstdev(overalls), 3)
    else:
        aggregated["dispersion"] = 0.0

    median_overall = statistics.median(overalls)
    representative = min(samples, key=lambda s: abs(s["overall"] - median_overall))
    aggregated["evidence"] = representative.get("evidence", {})
    aggregated["justification"] = representative.get("justification", "")
    aggregated["samples_used"] = len(samples)
    return aggregated


class StoryQualityJudge(ABC):
    @abstractmethod
    def evaluate(self, story: UserStory) -> dict:
        """Return a dict with completeness, specificity, feasibility,
        risk_coverage, language_consistency, overall, justification,
        evidence, dispersion, samples_used, judge_model."""
        ...


class StubQualityJudge(StoryQualityJudge):
    def evaluate(self, story: UserStory) -> dict:
        return {
            "completeness": 7.0,
            "specificity": 7.0,
            "feasibility": 7.0,
            "risk_coverage": 7.0,
            "language_consistency": 7.0,
            "overall": 7.0,
            "justification": "Stub evaluation",
            "evidence": {},
            "dispersion": 0.0,
            "samples_used": 1,
            "judge_model": "stub",
        }


def _collect_samples(call_once, n_samples: int) -> list[dict]:
    """Run the per-call closure N times, parse each result, drop failures.

    If every sample fails, propagate the last error so callers see it.
    """
    samples: list[dict] = []
    last_error: Exception | None = None
    for i in range(max(1, n_samples)):
        try:
            raw_text = call_once()
            raw = extract_json(raw_text)
            samples.append(_parse_scores(raw))
        except (ValueError, KeyError) as exc:
            last_error = exc
            logger.warning("Quality judge sample %d/%d failed: %s", i + 1, n_samples, exc)
    if not samples and last_error is not None:
        raise last_error
    return samples


class AnthropicQualityJudge(StoryQualityJudge):
    def __init__(self, settings: Settings) -> None:
        if _anthropic_lib is None:
            raise ImportError("anthropic package is required")
        self._client = _anthropic_lib.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self._model = settings.AI_JUDGE_MODEL or settings.AI_MODEL or "claude-haiku-4-5-20251001"
        self._n_samples = max(1, int(settings.AI_JUDGE_SAMPLES))
        self._temperature = float(settings.AI_JUDGE_TEMPERATURE)

    def evaluate(self, story: UserStory) -> dict:
        prompt = _build_prompt(story)

        def call_once() -> str:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=512,
                temperature=self._temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text

        samples = _collect_samples(call_once, self._n_samples)
        scores = _aggregate_samples(samples)
        scores["judge_model"] = self._model
        return scores


class OpenAIQualityJudge(StoryQualityJudge):
    def __init__(self, settings: Settings) -> None:
        if _openai_lib is None:
            raise ImportError("openai package is required")
        self._client = _openai_lib.OpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = settings.AI_JUDGE_MODEL or settings.AI_MODEL or "gpt-4o-mini"
        self._n_samples = max(1, int(settings.AI_JUDGE_SAMPLES))
        self._temperature = float(settings.AI_JUDGE_TEMPERATURE)

    def evaluate(self, story: UserStory) -> dict:
        prompt = _build_prompt(story)

        def call_once() -> str:
            response = self._client.chat.completions.create(
                model=self._model,
                max_tokens=512,
                temperature=self._temperature,
                response_format={"type": "json_object"},
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content

        samples = _collect_samples(call_once, self._n_samples)
        scores = _aggregate_samples(samples)
        scores["judge_model"] = self._model
        return scores


def get_quality_judge(settings: Settings = None) -> StoryQualityJudge:
    if settings is None:
        settings = get_settings()
    if not settings.AI_JUDGE_ENABLED:
        return StubQualityJudge()
    provider = settings.AI_JUDGE_PROVIDER or settings.AI_PROVIDER
    if provider == "anthropic":
        return AnthropicQualityJudge(settings)
    if provider == "openai":
        return OpenAIQualityJudge(settings)
    return StubQualityJudge()
