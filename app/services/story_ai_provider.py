from abc import ABC, abstractmethod

from app.core.config import Settings
from app.utils.json_utils import extract_json

_STUB_STORY_RESPONSE = {
    "title": "User Registration with Email Confirmation",
    "story_description": (
        "As a user, I want to register with my email and password "
        "so that I can access the platform securely."
    ),
    "acceptance_criteria": [
        "User can register with a valid email address",
        "Password must meet minimum security requirements",
        "System sends a confirmation email after registration",
    ],
    "technical_tasks": [
        "Create registration endpoint",
        "Implement email validation logic",
        "Add email confirmation service",
        "Write unit tests for registration flow",
    ],
    "definition_of_done": [
        "Code implemented and reviewed",
        "Unit tests passing with >80% coverage",
        "Deployed to staging environment",
    ],
    "risk_notes": [
        "Email delivery dependency on external service",
        "Backward compatibility with existing auth flow must be verified",
    ],
}

_STORY_PROMPT_TEMPLATE = """\
Eres un analista ágil de software senior. Dado el siguiente contexto técnico, genera una Historia de Usuario profesional y completa.

Contexto del requerimiento:
- Texto: "{requirement_text}"
- Intención: {intent}
- Tipo de cambio: {feature_type}
- Dominio de negocio: {business_domain}
- Complejidad estimada: {estimated_complexity}
- Palabras clave: {keywords}

Contexto del impacto técnico:
- Archivos impactados: {files_impacted}
- Módulos impactados: {modules_impacted}
- Nivel de riesgo: {risk_level}

Genera ÚNICAMENTE un JSON válido con estos campos exactos:
- title: string corto y descriptivo (máximo 80 caracteres)
- story_description: string en formato "As a [tipo de usuario], I want [acción] so that [beneficio]"
- acceptance_criteria: array de strings (mínimo 3 criterios verificables)
- technical_tasks: array de strings (mínimo 3 tareas técnicas concretas)
- definition_of_done: array de strings (mínimo 3 criterios de completitud)
- risk_notes: array de strings (riesgos identificados, puede ser vacío)

Sin texto adicional. Sin explicaciones. Solo el JSON válido.\
"""


class StoryAIProvider(ABC):
    @abstractmethod
    def generate_story(self, context: dict) -> dict:
        ...

    def _build_prompt(self, context: dict) -> str:
        return _STORY_PROMPT_TEMPLATE.format(
            requirement_text=context.get("requirement_text", ""),
            intent=context.get("intent", ""),
            feature_type=context.get("feature_type", ""),
            business_domain=context.get("business_domain", ""),
            estimated_complexity=context.get("estimated_complexity", ""),
            keywords=context.get("keywords", []),
            files_impacted=context.get("files_impacted", 0),
            modules_impacted=context.get("modules_impacted", 0),
            risk_level=context.get("risk_level", ""),
        )


class StubStoryProvider(StoryAIProvider):
    def generate_story(self, context: dict) -> dict:
        return dict(_STUB_STORY_RESPONSE)


class AnthropicStoryProvider(StoryAIProvider):
    def __init__(self, settings: Settings) -> None:
        import anthropic as _anthropic
        self._client = _anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self._model = settings.AI_MODEL or "claude-haiku-4-5-20251001"
        self._timeout = settings.AI_TIMEOUT_SECONDS

    def generate_story(self, context: dict) -> dict:
        prompt = self._build_prompt(context)
        response = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            temperature=0,
            timeout=self._timeout,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = response.content[0].text
        return extract_json(raw_text)


class OpenAIStoryProvider(StoryAIProvider):
    def __init__(self, settings: Settings) -> None:
        import openai as _openai
        self._client = _openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = settings.AI_MODEL or "gpt-4o-mini"
        self._timeout = settings.AI_TIMEOUT_SECONDS

    def generate_story(self, context: dict) -> dict:
        prompt = self._build_prompt(context)
        response = self._client.chat.completions.create(
            model=self._model,
            temperature=0,
            timeout=self._timeout,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = response.choices[0].message.content
        return extract_json(raw_text)


def get_story_ai_provider(settings: Settings) -> StoryAIProvider:
    if settings.AI_PROVIDER == "anthropic":
        return AnthropicStoryProvider(settings)
    if settings.AI_PROVIDER == "openai":
        return OpenAIStoryProvider(settings)
    return StubStoryProvider()
