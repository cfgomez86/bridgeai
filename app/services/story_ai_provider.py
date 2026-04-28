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
            {
                "title": "Crear componente RegisterForm con campos email y contraseña",
                "description": (
                    "Construir un formulario controlado en React con inputs de email, contraseña y confirmación. "
                    "Aplicar validaciones inline (formato de email, longitud mínima, coincidencia de contraseñas).\n\n"
                    "Archivos: frontend/components/auth/RegisterForm.tsx\n\n"
                    "Verificar: navegar a /register en dev, intentar enviar con campos vacíos o inválidos y confirmar mensajes de error."
                ),
            },
            {
                "title": "Añadir indicador visual de fortaleza de contraseña",
                "description": (
                    "Mostrar un medidor debajo del input de contraseña que evalúe longitud, mayúsculas, números y símbolos. "
                    "Reusar la lógica de evaluación en utils si ya existe.\n\n"
                    "Archivos: frontend/components/auth/RegisterForm.tsx\n\n"
                    "Verificar: tipear contraseñas de distinta complejidad y observar el cambio del medidor."
                ),
            },
        ],
        "backend": [
            {
                "title": "Crear endpoint POST /auth/register con validación de email",
                "description": (
                    "Definir la ruta FastAPI que reciba {email, password}, valide formato de email y reglas de seguridad de contraseña, "
                    "persista el usuario y devuelva 201.\n\n"
                    "Archivos: app/api/routes/auth.py, app/services/auth_service.py\n\n"
                    "Verificar: pytest tests/test_auth.py y curl manual al endpoint."
                ),
            },
            {
                "title": "Implementar servicio de envío de email de confirmación",
                "description": (
                    "Tras crear un usuario, encolar un email de confirmación con un token único. El token expira en 24h.\n\n"
                    "Archivos: app/services/email_service.py\n\n"
                    "Verificar: registrar un usuario en dev y revisar que el log de SMTP muestre el envío."
                ),
            },
        ],
        "configuration": [
            {
                "title": "Añadir variables SMTP al .env.example",
                "description": (
                    "Agregar SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD al .env.example y documentar en el README cómo obtenerlas.\n\n"
                    "Archivos: .env.example\n\n"
                    "Verificar: copiar .env.example a .env y arrancar la app sin errores de configuración."
                ),
            },
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
- subtasks: objeto con tres claves obligatorias ("frontend", "backend", "configuration"). Cada una es un array de objetos con dos claves: "title" y "description".
    * "title": string ≤150 caracteres, en imperativo, accionable. Describe la INTENCIÓN de la tarea SIN prefijo de categoría y SIN repetir la ruta de archivo. Ej: "Agregar campo descripción al ProductReadModelMapper".
    * "description": string multilínea (usa "\n\n" entre párrafos). Debe explicar: (1) QUÉ hacer en detalle, paso a paso si es necesario; (2) POR QUÉ es necesario o cómo conecta con la historia; (3) qué archivos del whitelist tocar (lista los paths exactos); (4) cómo verificarlo (qué tests correr, qué comportamiento observar). Mínimo 30 caracteres.
    * "frontend": tareas para presentación/UI. Si no hay archivos UI en el whitelist, deja el array vacío.
    * "backend": tareas para lógica de negocio, servicios, rutas, base de datos. Mínimo 2 tareas. Si no hay archivos verificables, describe sin path.
    * "configuration": infraestructura, variables de entorno, dependencias, migraciones, CI/CD. Si no aplica, array vacío.
    NUNCA inventes paths en title ni en description. La regla anti-alucinación aplica a ambos campos.
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
