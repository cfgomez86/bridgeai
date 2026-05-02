from abc import ABC, abstractmethod
from functools import lru_cache

from app.core.config import Settings, get_settings
from app.domain.coherence_result import CoherenceResult
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


VALID_REASON_CODES = {
    "non_software_request",
    "contradictory",
    "unintelligible",
    "conversational",
    "empty_intent",
}


class IncoherentRequirementError(ValueError):
    """Raised when the coherence pre-filter rejects a requirement as not actionable."""

    def __init__(
        self,
        warning: str,
        reason_codes: list[str],
        model_used: str | None = None,
    ) -> None:
        super().__init__(warning)
        self.warning = warning
        self.reason_codes = list(reason_codes)
        self.model_used = model_used


_COHERENCE_PROMPT = """\
Eres un validador de coherencia para una herramienta que genera historias
técnicas a partir de requerimientos en lenguaje natural. La herramienta
sirve a DOS perfiles:

1. Usuario técnico (developer, QA, DevOps): puede usar jerga (endpoints,
   tablas, tokens, jobs, hooks, latencia, etc.).
2. Product Owner / negocio: usa lenguaje funcional sin jerga (ej:
   "quiero que los clientes reciban un correo cuando se cancele un pedido").

AMBOS estilos son válidos. NO rechaces un requerimiento por estar escrito
en lenguaje funcional ni por estar muy técnico. Solo rechaza si el texto
claramente:
- No describe un sistema/software (ej: "una casa roja en la playa").
- Es contradictorio o imposible (ej: "al amanecer en la tarde").
- Es ininteligible o random ("asdfgh qwerty").
- Es una pregunta o conversación, no una solicitud ("¿cómo estás?", "hola").
- Está vacío de intención de cambio (no pide nada accionable).

Marca como COHERENTE incluso si:
- Es vago o corto: el sistema downstream se encarga de completar.
- Carece de detalles técnicos (común en POs): es válido.
- Mezcla idiomas o tiene errores de tipeo menores: si la intención se
  entiende, está bien.

EN LA DUDA, devuelve is_coherent=true.

Responde ÚNICAMENTE con un JSON con esta forma:
{{
  "is_coherent": boolean,
  "warning": string | null,
  "reason_codes": string[]
}}

- Si is_coherent=false: "warning" explica al usuario en SU idioma por qué
  no se puede procesar (máximo 2 frases, tono empático y constructivo —
  invitando a reformular). "reason_codes" es 1-3 códigos de
  [non_software_request, contradictory, unintelligible, conversational, empty_intent].
- Si is_coherent=true: "warning" es null y "reason_codes" es [].

Ejemplos:
- Técnico: "agregar endpoint POST /users con validación JWT" -> COHERENTE.
- PO: "quiero que los usuarios puedan recuperar su contraseña por correo" -> COHERENTE.
- PO vago: "necesito mejorar la experiencia del checkout" -> COHERENTE.
- Técnico vago: "refactorizar el módulo de auth" -> COHERENTE.
- Mezcla: "quiero algo bonito" -> COHERENTE (vago pero accionable).
- Absurdo: "una casa roja al amanecer en la tarde" -> INCOHERENTE
  -> {{"is_coherent": false, "warning": "El texto describe una escena, no un cambio de software. Reformula como una funcionalidad concreta del sistema.", "reason_codes": ["non_software_request", "contradictory"]}}
- Random: "asdf qwer" -> INCOHERENTE
  -> {{"is_coherent": false, "warning": "El texto no es legible. Describe brevemente la funcionalidad que necesitas.", "reason_codes": ["unintelligible"]}}
- Conversación: "hola, ¿cómo estás?" -> INCOHERENTE
  -> {{"is_coherent": false, "warning": "Esto parece un saludo. Describe el cambio o funcionalidad que quieres construir.", "reason_codes": ["conversational"]}}

Texto a evaluar:
"{requirement_text}"

Responde SOLO con el JSON. Sin markdown, sin explicaciones.\
"""


def _parse_coherence_response(raw_text: str) -> CoherenceResult:
    payload = extract_json(raw_text)
    if "is_coherent" not in payload:
        raise ValueError(f"Coherence response missing 'is_coherent': {raw_text[:200]}")
    is_coherent = bool(payload["is_coherent"])
    warning = payload.get("warning") if not is_coherent else None
    if warning is not None and not isinstance(warning, str):
        warning = str(warning)
    raw_codes = payload.get("reason_codes") or []
    if not isinstance(raw_codes, list):
        raw_codes = []
    reason_codes = [str(c) for c in raw_codes if isinstance(c, str)]
    if is_coherent:
        reason_codes = []
    return CoherenceResult(
        is_coherent=is_coherent,
        warning=warning if not is_coherent else None,
        reason_codes=reason_codes,
    )


class RequirementCoherenceValidator(ABC):
    model_name: str = ""

    @abstractmethod
    def validate(self, requirement_text: str) -> CoherenceResult:
        ...

    def _build_prompt(self, requirement_text: str) -> str:
        # Use replace() so user-supplied braces or quotes cannot break .format() interpolation.
        return _COHERENCE_PROMPT.replace("{requirement_text}", requirement_text)


class StubCoherenceValidator(RequirementCoherenceValidator):
    """Always returns is_coherent=True. Used when AI_PROVIDER is stub or
    when no real model is configured. Keeps tests deterministic."""

    model_name = "stub"

    def validate(self, requirement_text: str) -> CoherenceResult:
        return CoherenceResult(is_coherent=True, warning=None, reason_codes=[])


class AnthropicCoherenceValidator(RequirementCoherenceValidator):
    def __init__(self, settings: Settings) -> None:
        if _anthropic_lib is None:
            raise ImportError("anthropic package is required")
        self._client = _anthropic_lib.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self._model = (
            settings.AI_JUDGE_MODEL
            or settings.AI_MODEL
            or settings.ANTHROPIC_MODEL
        )
        self._timeout = settings.AI_TIMEOUT_SECONDS
        self._max_tokens = settings.AI_COHERENCE_MAX_TOKENS
        self.model_name = self._model

    def validate(self, requirement_text: str) -> CoherenceResult:
        prompt = self._build_prompt(requirement_text)
        response = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            temperature=0,
            timeout=self._timeout,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = response.content[0].text
        return _parse_coherence_response(raw_text)


class OpenAICoherenceValidator(RequirementCoherenceValidator):
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
        self._model = (
            settings.AI_JUDGE_MODEL
            or settings.AI_MODEL
            or default_model
        )
        self._timeout = settings.AI_TIMEOUT_SECONDS
        self._max_tokens = settings.AI_COHERENCE_MAX_TOKENS
        self.model_name = self._model

    def validate(self, requirement_text: str) -> CoherenceResult:
        prompt = self._build_prompt(requirement_text)
        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=self._max_tokens,
            temperature=0,
            timeout=self._timeout,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = response.choices[0].message.content
        return _parse_coherence_response(raw_text)


class GeminiCoherenceValidator(RequirementCoherenceValidator):
    def __init__(self, settings: Settings) -> None:
        if _genai_lib is None:
            raise ImportError("google-genai package is required")
        self._client = _genai_lib.Client(api_key=settings.GEMINI_API_KEY)
        self._model = (
            settings.AI_JUDGE_MODEL
            or settings.AI_MODEL
            or settings.GEMINI_MODEL
        )
        self._max_tokens = settings.AI_COHERENCE_MAX_TOKENS
        self.model_name = self._model

    def validate(self, requirement_text: str) -> CoherenceResult:
        prompt = self._build_prompt(requirement_text)
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=_genai_types.GenerateContentConfig(
                temperature=0,
                max_output_tokens=self._max_tokens,
                response_mime_type="application/json",
                thinking_config=_genai_types.ThinkingConfig(thinking_budget=0),
            ),
        )
        return _parse_coherence_response(response.text)


@lru_cache(maxsize=None)
def _build_validator(provider_key: str, model_key: str) -> RequirementCoherenceValidator:
    """Cached factory keyed on primitive strings — consistent with the @lru_cache
    pattern used by get_settings() and get_ai_provider() elsewhere in the codebase."""
    settings = get_settings()
    if provider_key == "anthropic":
        return AnthropicCoherenceValidator(settings)
    if provider_key == "openai":
        return OpenAICoherenceValidator(settings, default_model=settings.OPENAI_MODEL)
    if provider_key == "groq":
        return OpenAICoherenceValidator(
            settings,
            api_key=settings.GROQ_API_KEY,
            base_url=settings.GROQ_BASE_URL,
            default_model=settings.GROQ_MODEL,
        )
    if provider_key == "gemini":
        return GeminiCoherenceValidator(settings)
    return StubCoherenceValidator()


def get_coherence_validator(settings: Settings) -> RequirementCoherenceValidator:
    provider_key = settings.AI_JUDGE_PROVIDER or settings.AI_PROVIDER
    model_key = settings.AI_JUDGE_MODEL or settings.AI_MODEL or ""
    return _build_validator(provider_key, model_key)
