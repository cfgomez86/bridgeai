"""LLM-as-Judge quality evaluator for UserStory objects."""

import logging
import statistics
import time
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

try:
    from google import genai as _genai_lib
    from google.genai import types as _genai_types
except ImportError:
    _genai_lib = None  # type: ignore[assignment]
    _genai_types = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

_DIMENSIONS = ("completeness", "specificity", "feasibility", "risk_coverage", "language_consistency")

_JUDGE_PROMPT_TEMPLATE = """\
Eres un revisor senior de historias de usuario ágiles. Eres exigente: solo das 9-10 cuando se cumplen \
TODAS las condiciones del anclaje superior. Si dudas entre dos bandas, baja la nota.

{requirement_block}\
PARTE 1 — CLASIFICACIÓN BINARIA OBLIGATORIA (responde con honestidad, NO ajustes scores tú mismo):

  is_actionable_requirement (true/false):
    Marca FALSE si el requerimiento original es:
      • Una sola palabra-sustantivo (p.ej. "rabbit", "login", "data").
      • Una frase sin verbo de acción claro o sin objeto.
      • Un nombre de campo/método aislado sin entidad de negocio plausible (p.ej. "agregar campo \
volar" — el campo no tiene sentido en el dominio implícito; un PO real lo rechazaría).
      • Un requerimiento sin propósito de negocio entendible (¿para qué? ¿qué problema resuelve?).
    Marca TRUE solo si un PO razonable lo aceptaría como entrada de refinement sin pedir aclaraciones.

  story_addresses_requirement (true/false):
    Marca FALSE si la historia inventa un dominio distinto, completa un requerimiento vago con \
suposiciones no verificables, o construye algo no implícito en el texto original.
    Marca TRUE solo si la historia es la traducción fiel del requerimiento al formato de historia.

PARTE 2 — Evalúa la siguiente historia en cinco dimensiones (0-10) usando esta rúbrica anclada.
Puntúa según la rúbrica SIN considerar la alineación (eso lo aplicamos en código a partir de la \
clasificación binaria de la Parte 1):

completeness — ¿la historia cubre todo lo necesario Y aborda el requerimiento original?
  9-10: aborda el requerimiento + descripción + ≥3 AC verificables + DoD explícito + subtareas frontend/backend/config + notas de riesgo coherentes.
  7-8 : la mayoría de los anteriores presentes; falta uno menor.
  5-6 : AC presentes pero DoD o subtareas escasas/genéricas, o cobertura parcial del requerimiento.
  3-4 : falta más de un bloque importante, o solo aborda tangencialmente el requerimiento.
  0-2 : solo título y descripción sin AC ni subtareas reales, O la historia no aborda el requerimiento.

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
  "alignment": {{
    "is_actionable_requirement": <true|false>,
    "story_addresses_requirement": <true|false>
  }},
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


def _build_prompt(
    story: UserStory,
    requirement_text: str | None = None,
    requirement_intent: str | None = None,
    entity_not_found: bool = False,
) -> str:
    subtasks_backend = story.subtasks.get("backend", [])[:3]
    if requirement_text:
        intent_line = f"Intent detectada: {requirement_intent}\n" if requirement_intent else ""
        force_line = (
            "⚠️ La entidad principal del requerimiento NO existía en el codebase indexado al "
            "generar la historia. El usuario fue advertido y aun así forzó la creación. Si el "
            "requerimiento sigue siendo vago/no accionable, marca is_actionable_requirement=false; "
            "una entidad ausente no puede compensar un requerimiento débil.\n"
            if entity_not_found else ""
        )
        requirement_block = (
            "REQUERIMIENTO ORIGINAL (ancla la evaluación):\n"
            f"{requirement_text[:600]}\n"
            f"{intent_line}{force_line}\n"
        )
    else:
        requirement_block = ""
    return _JUDGE_PROMPT_TEMPLATE.format(
        requirement_block=requirement_block,
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

    # Apply hard caps based on the binary alignment classification. We do this in
    # code (not by trusting the model to lower its own dimension scores) because
    # LLM judges have a strong bias toward rewarding well-formed output even when
    # the underlying requirement is incoherent.
    alignment_raw = raw.get("alignment") if isinstance(raw.get("alignment"), dict) else {}
    is_actionable = bool(alignment_raw.get("is_actionable_requirement", True))
    addresses_req = bool(alignment_raw.get("story_addresses_requirement", True))
    if not is_actionable:
        scores["completeness"] = min(scores["completeness"], 3.0)
        scores["specificity"]  = min(scores["specificity"],  4.0)
        scores["feasibility"]  = min(scores["feasibility"],  4.0)
    if not addresses_req:
        scores["completeness"] = min(scores["completeness"], 2.0)
        scores["specificity"]  = min(scores["specificity"],  3.0)
    scores["alignment"] = {
        "is_actionable_requirement": is_actionable,
        "story_addresses_requirement": addresses_req,
    }

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
    def evaluate(
        self,
        story: UserStory,
        requirement_text: str | None = None,
        requirement_intent: str | None = None,
        entity_not_found: bool = False,
    ) -> dict:
        """Return a dict with completeness, specificity, feasibility,
        risk_coverage, language_consistency, overall, justification,
        evidence, dispersion, samples_used, judge_model.

        When `requirement_text` is provided the judge anchors `completeness`
        to whether the story actually addresses the requirement (hard cap
        of 2 if disconnected). Without it, alignment is not scored."""
        ...


class StubQualityJudge(StoryQualityJudge):
    def evaluate(
        self,
        story: UserStory,
        requirement_text: str | None = None,
        requirement_intent: str | None = None,
        entity_not_found: bool = False,
    ) -> dict:
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
        self._model = settings.AI_JUDGE_MODEL or settings.ANTHROPIC_MODEL
        self._n_samples = max(1, int(settings.AI_JUDGE_SAMPLES))
        self._temperature = float(settings.AI_JUDGE_TEMPERATURE)
        self._max_tokens = settings.AI_JUDGE_MAX_TOKENS

    def evaluate(
        self,
        story: UserStory,
        requirement_text: str | None = None,
        requirement_intent: str | None = None,
        entity_not_found: bool = False,
    ) -> dict:
        prompt = _build_prompt(story, requirement_text, requirement_intent, entity_not_found)

        def call_once() -> str:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                temperature=self._temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text

        samples = _collect_samples(call_once, self._n_samples)
        scores = _aggregate_samples(samples)
        scores["judge_model"] = self._model
        return scores


class OpenAIQualityJudge(StoryQualityJudge):
    def __init__(
        self,
        settings: Settings,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        default_model: str = "gpt-4o-mini",
    ) -> None:
        if _openai_lib is None:
            raise ImportError("openai package is required")
        self._client = _openai_lib.OpenAI(
            api_key=api_key or settings.OPENAI_API_KEY,
            base_url=base_url,
        )
        self._model = settings.AI_JUDGE_MODEL or default_model
        self._n_samples = max(1, int(settings.AI_JUDGE_SAMPLES))
        self._temperature = float(settings.AI_JUDGE_TEMPERATURE)
        self._max_tokens = settings.AI_JUDGE_MAX_TOKENS

    def evaluate(
        self,
        story: UserStory,
        requirement_text: str | None = None,
        requirement_intent: str | None = None,
        entity_not_found: bool = False,
    ) -> dict:
        prompt = _build_prompt(story, requirement_text, requirement_intent, entity_not_found)

        def call_once() -> str:
            response = self._client.chat.completions.create(
                model=self._model,
                max_tokens=self._max_tokens,
                temperature=self._temperature,
                response_format={"type": "json_object"},
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content

        samples = _collect_samples(call_once, self._n_samples)
        scores = _aggregate_samples(samples)
        scores["judge_model"] = self._model
        return scores


class GeminiQualityJudge(StoryQualityJudge):
    def __init__(self, settings: Settings) -> None:
        if _genai_lib is None:
            raise ImportError("google-genai package is required")
        self._client = _genai_lib.Client(api_key=settings.GEMINI_API_KEY)
        self._model = settings.AI_JUDGE_MODEL or settings.GEMINI_MODEL
        self._n_samples = max(1, int(settings.AI_JUDGE_SAMPLES))
        self._temperature = float(settings.AI_JUDGE_TEMPERATURE)
        self._max_tokens = settings.AI_JUDGE_MAX_TOKENS

    def evaluate(
        self,
        story: UserStory,
        requirement_text: str | None = None,
        requirement_intent: str | None = None,
        entity_not_found: bool = False,
    ) -> dict:
        prompt = _build_prompt(story, requirement_text, requirement_intent, entity_not_found)
        _max_retries = 3
        _retry_delays = [5, 10, 20]

        def call_once() -> str:
            last_exc: Exception | None = None
            for attempt in range(_max_retries):
                try:
                    response = self._client.models.generate_content(
                        model=self._model,
                        contents=prompt,
                        config=_genai_types.GenerateContentConfig(
                            temperature=self._temperature,
                            max_output_tokens=self._max_tokens,
                            response_mime_type="application/json",
                            thinking_config=_genai_types.ThinkingConfig(thinking_budget=0),
                        ),
                    )
                    # Detect MAX_TOKENS / SAFETY truncations explicitly. Cuando el
                    # finish_reason no es STOP/MODEL_LENGTH-OK, response.text suele
                    # venir vacío y el SDK lanza una excepción opaca al accederlo.
                    finish_reason = None
                    candidates = getattr(response, "candidates", None) or []
                    if candidates:
                        finish_reason = getattr(candidates[0], "finish_reason", None)
                    text = getattr(response, "text", None)
                    if not text:
                        reason = str(finish_reason) if finish_reason else "unknown"
                        raise ValueError(
                            f"Gemini judge returned empty text (finish_reason={reason}); "
                            f"raise AI_JUDGE_MAX_TOKENS (current={self._max_tokens})."
                        )
                    return text
                except ValueError:
                    raise
                except Exception as exc:
                    code = str(exc)[:3]
                    if code in ("429", "503") and attempt < _max_retries - 1:
                        wait = _retry_delays[attempt]
                        logger.warning(
                            "Gemini judge transient error %s (attempt %d/%d), retrying in %ds",
                            code, attempt + 1, _max_retries, wait,
                        )
                        time.sleep(wait)
                        last_exc = exc
                        continue
                    raise
            raise last_exc  # type: ignore[misc]

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
        return OpenAIQualityJudge(settings, default_model=settings.OPENAI_MODEL)
    if provider == "groq":
        return OpenAIQualityJudge(
            settings,
            api_key=settings.GROQ_API_KEY,
            base_url=settings.GROQ_BASE_URL,
            default_model=settings.GROQ_MODEL,
        )
    if provider == "gemini":
        return GeminiQualityJudge(settings)
    return StubQualityJudge()
