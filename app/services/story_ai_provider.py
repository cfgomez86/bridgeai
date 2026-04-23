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

_provider_cache: dict[str, "StoryAIProvider"] = {}

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
    "subtasks": {
        "frontend": [
            "Create registration form component with email/password fields",
            "Add client-side validation for password strength indicator",
        ],
        "backend": [
            "Create POST /auth/register endpoint in app/api/routes/auth.py",
            "Implement email validation logic in app/services/auth_service.py",
            "Add email confirmation service in app/services/email_service.py",
            "Write unit tests for registration flow in tests/test_auth.py",
        ],
        "configuration": [
            "Add SMTP_HOST, SMTP_PORT, SMTP_USER env variables to .env.example",
        ],
    },
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

REGLAS ESTRICTAS — VIOLARLAS INVALIDA LA RESPUESTA:
1. PROHIBIDO inventar rutas de archivo. Solo puedes citar paths que aparezcan LITERALMENTE en la sección "Archivos disponibles del codebase". Copiar exacto.
2. Si ningún archivo del whitelist encaja con una subtarea, descríbela SIN mencionar archivo específico. Mejor vago que inventado.
3. NUNCA uses ejemplos genéricos tipo "app/routes/X.py", "src/Foo.java", "app/components/Bar.tsx". Ese tipo de paths son señal de invención.
4. El whitelist refleja el lenguaje real del repo. Si el repo es Java, no pongas paths .py ni .tsx. Si es Python, no pongas .java. Respeta las extensiones existentes en el whitelist.
{hallucination_warning}
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
- Archivos concretos del codebase identificados por el análisis como más relevantes:
{impacted_file_paths_formatted}

Archivos disponibles del codebase (whitelist exhaustiva — NO puedes citar nada fuera de esta lista):
{available_file_paths_formatted}

Genera ÚNICAMENTE un JSON válido con estos campos exactos:
- title: string corto y descriptivo (máximo 80 caracteres)
- story_description: string en formato de historia de usuario estándar: "Como [tipo de usuario], quiero [acción] para que [beneficio]". Usa el mismo idioma que el texto del requerimiento.
- acceptance_criteria: array de strings (mínimo 3 criterios verificables)
- subtasks: objeto con tres claves obligatorias, cada una con un array de strings:
    * "frontend": tareas para la capa de presentación/UI. Si hay archivos del whitelist relacionados a UI, referéncialos exactamente; si no hay, describe la tarea sin archivo o deja el array vacío.
    * "backend": tareas para la lógica de negocio, servicios, rutas y base de datos. Si hay archivos del whitelist aplicables, referéncialos exactamente; si no hay, describe la tarea SIN path. Mínimo 2 tareas, aunque sea sin path.
    * "configuration": tareas de infraestructura, variables de entorno, dependencias, scripts de migración o CI/CD. Si no aplica, devuelve array vacío.
    Usa los archivos impactados y el whitelist para decidir categorías. NUNCA inventes paths.
- definition_of_done: array de strings (mínimo 3 criterios de completitud)
- risk_notes: array de strings con riesgos técnicos específicos. Considera siempre:
    * Invalidación de caché si el requerimiento afecta parámetros de generación (ej: idioma, configuración)
    * Consistencia de idioma en outputs del LLM (riesgo de mezcla de idiomas en respuestas estructuradas)
    * Regresiones en features existentes conectadas a los archivos impactados
    * Cobertura de tests para los módulos modificados
    Si no aplica ninguno, devuelve array vacío.

IMPORTANTE: Genera TODOS los valores del JSON en este idioma: {language}.
Sin texto adicional. Sin explicaciones. Solo el JSON válido.\
"""


class StoryAIProvider(ABC):
    @abstractmethod
    def generate_story(self, context: dict) -> dict:
        ...

    def _build_prompt(self, context: dict) -> str:
        paths = context.get("impacted_file_paths", [])
        formatted_paths = "\n".join(f"  - {p}" for p in paths) if paths else "  (no hay archivos específicos identificados)"
        available = context.get("available_file_paths", [])
        formatted_available = (
            "\n".join(f"  - {p}" for p in available)
            if available
            else "  (whitelist vacía — NO cites ningún archivo en las subtareas)"
        )
        hallucinated = context.get("hallucinated_last_attempt") or []
        hallucination_warning = ""
        if hallucinated:
            joined = ", ".join(hallucinated[:20])
            hallucination_warning = (
                "\nATENCIÓN: tu intento anterior incluyó rutas INVENTADAS que NO existen en el codebase: "
                f"{joined}. No vuelvas a usarlas; limita los paths estrictamente al whitelist.\n"
            )
        language_names = {
            "es": "español", "en": "English", "fr": "français",
            "de": "Deutsch", "pt": "português",
        }
        lang_code = context.get("language", "es")
        language_label = language_names.get(lang_code, lang_code)
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
            impacted_file_paths_formatted=formatted_paths,
            available_file_paths_formatted=formatted_available,
            hallucination_warning=hallucination_warning,
            language=language_label,
        )


class StubStoryProvider(StoryAIProvider):
    def generate_story(self, context: dict) -> dict:
        return dict(_STUB_STORY_RESPONSE)


class AnthropicStoryProvider(StoryAIProvider):
    def __init__(self, settings: Settings) -> None:
        if _anthropic_lib is None:
            raise ImportError("anthropic package is required")
        self._client = _anthropic_lib.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self._model = settings.AI_MODEL or "claude-haiku-4-5-20251001"
        self._timeout = settings.AI_TIMEOUT_SECONDS

    def generate_story(self, context: dict) -> dict:
        prompt = self._build_prompt(context)
        response = self._client.messages.create(
            model=self._model,
            max_tokens=2048,
            temperature=0,
            timeout=self._timeout,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = response.content[0].text
        return extract_json(raw_text)


class OpenAIStoryProvider(StoryAIProvider):
    def __init__(self, settings: Settings) -> None:
        if _openai_lib is None:
            raise ImportError("openai package is required")
        self._client = _openai_lib.OpenAI(api_key=settings.OPENAI_API_KEY)
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
    key = settings.AI_PROVIDER
    if key not in _provider_cache:
        if key == "anthropic":
            _provider_cache[key] = AnthropicStoryProvider(settings)
        elif key == "openai":
            _provider_cache[key] = OpenAIStoryProvider(settings)
        else:
            _provider_cache[key] = StubStoryProvider()
    return _provider_cache[key]
