"""LLM-as-Judge quality evaluator for UserStory objects."""

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

_JUDGE_PROMPT_TEMPLATE = """\
Eres un experto en metodologías ágiles. Evalúa la siguiente historia de usuario en cinco dimensiones, \
asignando una puntuación del 0 al 10 a cada una. Responde ÚNICAMENTE con JSON válido.

Historia de usuario:
Título: {title}
Descripción: {story_description}
Criterios de aceptación: {acceptance_criteria}
Subtareas (backend): {subtasks_backend}
Definición de terminado: {definition_of_done}
Notas de riesgo: {risk_notes}
Story points: {story_points}
Nivel de riesgo: {risk_level}

Dimensiones a evaluar:
- completeness: ¿La historia cubre todos los aspectos necesarios? (criterios de aceptación, DoD, subtareas)
- specificity: ¿Los criterios de aceptación son verificables y concretos?
- feasibility: ¿La historia es implementable en un sprint normal dada su complejidad?
- risk_coverage: ¿Las notas de riesgo abordan los riesgos técnicos más relevantes?
- language_consistency: ¿El idioma es consistente en todos los campos?

Responde ÚNICAMENTE con JSON válido:
{{
  "completeness": <0-10>,
  "specificity": <0-10>,
  "feasibility": <0-10>,
  "risk_coverage": <0-10>,
  "language_consistency": <0-10>,
  "justification": "<una o dos frases explicando los puntos débiles principales>"
}}
Sin texto adicional. Solo el JSON.\
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


def _parse_scores(raw: dict) -> dict:
    """Validate and normalise the LLM JSON response."""
    required = {"completeness", "specificity", "feasibility", "risk_coverage", "language_consistency"}
    missing = required - raw.keys()
    if missing:
        raise ValueError(f"Judge response missing fields: {missing}")

    scores = {k: float(raw[k]) for k in required}
    scores["overall"] = round(sum(scores.values()) / len(scores), 2)
    scores["justification"] = str(raw.get("justification", ""))
    return scores


class StoryQualityJudge(ABC):
    @abstractmethod
    def evaluate(self, story: UserStory) -> dict:
        """Return a dict with completeness, specificity, feasibility,
        risk_coverage, language_consistency, overall, justification, judge_model."""
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
            "judge_model": "stub",
        }


class AnthropicQualityJudge(StoryQualityJudge):
    def __init__(self, settings: Settings) -> None:
        if _anthropic_lib is None:
            raise ImportError("anthropic package is required")
        self._client = _anthropic_lib.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        model = settings.AI_JUDGE_MODEL or settings.AI_MODEL or "claude-haiku-4-5-20251001"
        self._model = model

    def evaluate(self, story: UserStory) -> dict:
        prompt = _build_prompt(story)
        response = self._client.messages.create(
            model=self._model,
            max_tokens=512,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = response.content[0].text
        raw = extract_json(raw_text)
        scores = _parse_scores(raw)
        scores["judge_model"] = self._model
        return scores


class OpenAIQualityJudge(StoryQualityJudge):
    def __init__(self, settings: Settings) -> None:
        if _openai_lib is None:
            raise ImportError("openai package is required")
        self._client = _openai_lib.OpenAI(api_key=settings.OPENAI_API_KEY)
        model = settings.AI_JUDGE_MODEL or settings.AI_MODEL or "gpt-4o-mini"
        self._model = model

    def evaluate(self, story: UserStory) -> dict:
        prompt = _build_prompt(story)
        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=512,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = response.choices[0].message.content
        raw = extract_json(raw_text)
        scores = _parse_scores(raw)
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
