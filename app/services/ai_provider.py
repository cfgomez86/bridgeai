from abc import ABC, abstractmethod

from app.core.config import Settings
from app.utils.json_utils import extract_json

try:
    import anthropic as _anthropic_lib
except ImportError:
    _anthropic_lib = None  # type: ignore[assignment]

try:
    import openai as _openai_lib
except ImportError:
    _openai_lib = None  # type: ignore[assignment]

_provider_cache: dict[str, "AIProvider"] = {}


VALID_FEATURE_TYPES = {"feature", "bugfix", "refactor", "enhancement", "configuration", "performance", "security"}
VALID_COMPLEXITIES = {"LOW", "MEDIUM", "HIGH"}
VALID_DOMAINS = {
    "authentication", "billing", "orders", "notifications", "reporting",
    "integration", "user_management", "configuration", "ui_ux", "devops",
    "data_management",
}
VALID_SCOPES = {"backend", "frontend", "fullstack", "infrastructure", "data"}

_STUB_RESPONSE = {
    "intent": "create_feature",
    "action": "create",
    "entity": "user",
    "feature_type": "feature",
    "priority": "medium",
    "business_domain": "user_management",
    "technical_scope": "backend",
    "estimated_complexity": "MEDIUM",
    "keywords": ["user", "feature"],
}

_PROMPT_TEMPLATE = """\
Eres un analista funcional de software. Analiza el siguiente requerimiento y devuelve ÚNICAMENTE un JSON válido.

Campos obligatorios del JSON:
- intent: descripción concisa de la intención (snake_case, ej: "create_user_account")
- action: verbo principal (create, update, delete, read, validate, notify, configure)
- entity: entidad principal del dominio (sustantivo en singular, ej: "user")
- feature_type: uno de [feature, bugfix, refactor, enhancement, configuration, performance, security]
- priority: uno de [low, medium, high]
- business_domain: uno de los siguientes (elige el más específico):
    authentication (login, tokens, permisos), billing (pagos, suscripciones),
    orders (pedidos, carrito), notifications (emails, alertas, push),
    reporting (dashboards, métricas, exports), integration (APIs externas, webhooks),
    user_management (usuarios, roles, perfiles), configuration (ajustes, preferencias, flags),
    ui_ux (interfaz, diseño, accesibilidad), devops (infra, CI/CD, despliegue),
    data_management (migraciones, modelos de datos, storage)
- technical_scope: uno de [backend, frontend, fullstack, infrastructure, data]
- estimated_complexity: uno de [LOW, MEDIUM, HIGH]
- keywords: array de strings con términos clave del requerimiento (máximo 8)

Reglas de complejidad:
- LOW: cambio simple, un archivo, sin nueva lógica
- MEDIUM: lógica nueva, validaciones, múltiples funciones
- HIGH: cambio arquitectónico, múltiples módulos, nuevo subsistema

Ejemplos de clasificación correcta (few-shot):
- "quiero elegir el idioma de la interfaz" → business_domain: configuration, technical_scope: frontend, estimated_complexity: MEDIUM
- "quiero activar notificaciones push al completar un pedido" → business_domain: notifications, technical_scope: fullstack, estimated_complexity: MEDIUM
- "quiero ver un dashboard con métricas de ventas mensuales" → business_domain: reporting, technical_scope: frontend, estimated_complexity: HIGH
- "quiero poder restablecer mi contraseña por correo" → business_domain: authentication, technical_scope: fullstack, estimated_complexity: MEDIUM
- "quiero configurar las reglas de generación de historias" → business_domain: configuration, technical_scope: fullstack, estimated_complexity: LOW

Requerimiento a analizar:
"{requirement_text}"

Responde ÚNICAMENTE con el JSON. Sin texto adicional, sin explicaciones, sin markdown.\
"""


class AIProvider(ABC):
    @abstractmethod
    def parse_requirement(self, requirement_text: str) -> dict:
        ...

    def _build_prompt(self, requirement_text: str) -> str:
        return _PROMPT_TEMPLATE.format(requirement_text=requirement_text)


class StubAIProvider(AIProvider):
    def parse_requirement(self, requirement_text: str) -> dict:
        return dict(_STUB_RESPONSE)


class AnthropicAIProvider(AIProvider):
    def __init__(self, settings: Settings) -> None:
        if _anthropic_lib is None:
            raise ImportError("anthropic package is required")
        self._client = _anthropic_lib.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self._model = settings.AI_MODEL or "claude-haiku-4-5-20251001"
        self._timeout = settings.AI_TIMEOUT_SECONDS

    def parse_requirement(self, requirement_text: str) -> dict:
        prompt = self._build_prompt(requirement_text)
        response = self._client.messages.create(
            model=self._model,
            max_tokens=512,
            temperature=0,
            timeout=self._timeout,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = response.content[0].text
        return extract_json(raw_text)


class OpenAIAIProvider(AIProvider):
    def __init__(self, settings: Settings) -> None:
        if _openai_lib is None:
            raise ImportError("openai package is required")
        self._client = _openai_lib.OpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = settings.AI_MODEL or "gpt-4o-mini"
        self._timeout = settings.AI_TIMEOUT_SECONDS

    def parse_requirement(self, requirement_text: str) -> dict:
        prompt = self._build_prompt(requirement_text)
        response = self._client.chat.completions.create(
            model=self._model,
            temperature=0,
            timeout=self._timeout,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = response.choices[0].message.content
        return extract_json(raw_text)


def get_ai_provider(settings: Settings) -> AIProvider:
    key = settings.AI_PROVIDER
    if key not in _provider_cache:
        if key == "anthropic":
            _provider_cache[key] = AnthropicAIProvider(settings)
        elif key == "openai":
            _provider_cache[key] = OpenAIAIProvider(settings)
        else:
            _provider_cache[key] = StubAIProvider()
    return _provider_cache[key]
