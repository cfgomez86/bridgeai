import hashlib
import threading
import time
from abc import ABC, abstractmethod

from app.core.config import Settings
from app.core.logging import get_logger
from app.utils.json_utils import extract_json
from app.utils.token_logging import log_token_usage

_logger = get_logger(__name__)

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

_provider_cache: dict[str, "StoryAIProvider"] = {}

_STUB_STORY_RESPONSE = {
    "title": "User Registration with Email Confirmation",
    "story_description": (
        "As a user, I want to register with my email and password "
        "so that I can access the platform securely."
    ),
    "acceptance_criteria": [
        "Given an unauthenticated visitor, When they submit the registration form with a valid email and a password of at least 8 characters, Then the account is created and a confirmation message is shown on screen.",
        "Given a visitor submitting an invalid email or a password shorter than 8 characters, When they press submit, Then the form displays an inline validation error and the registration is not performed.",
        "Given a newly registered user, When the registration succeeds, Then a confirmation email is sent to their inbox and remains valid for 24 hours.",
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

# Static portion of the prompt: rules + whitelist. Sent as a cached block so the large
# file list is not re-processed on quality/hallucination retries.
_STORY_STATIC_TEMPLATE = """\
Eres un analista ágil de software senior. Dado el siguiente contexto técnico, genera una Historia de Usuario profesional y completa.

REGLAS ESTRICTAS — VIOLARLAS INVALIDA LA RESPUESTA:
1. PROHIBIDO inventar rutas de archivo. Solo puedes citar paths que aparezcan LITERALMENTE en la sección "Archivos disponibles del codebase". Copiar exacto.
2. Si ningún archivo del whitelist encaja con una subtarea, descríbela SIN mencionar archivo específico. Mejor vago que inventado.
3. NUNCA uses ejemplos genéricos tipo "app/routes/X.py", "src/Foo.java", "app/components/Bar.tsx". Ese tipo de paths son señal de invención.
4. El whitelist refleja el lenguaje real del repo. Si el repo es Java, no pongas paths .py ni .tsx. Si es Python, no pongas .java. Respeta las extensiones existentes en el whitelist.
5. Cada criterio de aceptación DEBE seguir el formato Given/When/Then verificable, en el idioma de salida (es: "Dado ... Cuando ... Entonces ..."; en: "Given ... When ... Then ..."; pt/fr/de equivalentes). Resultados medibles, sin frases vagas. Mínimo 3 AC.
   IMPORTANTE — los AC son LENGUAJE DE PRODUCT OWNER, no de implementación. Describen COMPORTAMIENTO OBSERVABLE por el usuario en términos de negocio.
   PROHIBIDO en los AC (estos detalles van en subtasks/risk_notes, NO en AC):
     • Rutas o nombres de archivo (p.ej. "app/services/auth.py", "frontend/components/Foo.tsx").
     • Códigos HTTP (p.ej. "responde 201", "devuelve 404", "status 500").
     • Métodos REST y endpoints (p.ej. "POST /api/users", "llamada a GET /v1/orders").
     • Nombres de clases, módulos, funciones, tablas o columnas (p.ej. "AuthService", "user_id", "users.email").
     • Librerías, frameworks o lenguajes (p.ej. "FastAPI", "React", "JWT", "SQLAlchemy").
     • Detalles de implementación (queries SQL, hashing, formatos JSON, headers).
   PERMITIDO en los AC: elementos de UI visibles por nombre ("botón 'Crear cuenta'", "mensaje 'Cuenta creada'", "campo 'Email'", "pantalla de bienvenida"), tiempos de respuesta percibidos por el usuario ("en menos de 2 segundos"), reglas de negocio ("contraseña de al menos 8 caracteres").
   Ejemplo VÁLIDO (es): "Dado un visitante no autenticado, Cuando envía el formulario de registro con email válido y contraseña de al menos 8 caracteres, Entonces se crea la cuenta y se muestra el mensaje 'Cuenta creada'."
   Ejemplo VÁLIDO (en): "Given an unauthenticated visitor, When they submit the registration form with a valid email and a password of at least 8 characters, Then the account is created and the message 'Account created' is shown."
   Ejemplo INVÁLIDO (vago): "El sistema permite el registro" — sin G/W/T y sin resultado medible.
   Ejemplo INVÁLIDO (técnico): "Dado un cliente, Cuando hace POST /api/users con email y password, Entonces app/services/auth_service.py responde 201 y guarda en la tabla users." — paths, HTTP, endpoints y nombres de archivo NO van en AC.
6. Subtareas frontend: solo OBLIGATORIAS si la historia implica interfaz de usuario (formularios, pantallas, listas, dashboards, modales, vistas, botones). En ese caso devuelve ≥2 tareas que cubran (a) estructura del componente o pantalla, (b) validaciones / estados de UI / mensajes de error, (c) integración con la API. Si no hay archivos UI en el whitelist, describe el componente NUEVO a crear sin inventar paths concretos. Si la historia es PURAMENTE backend (endpoint sin UI, job, cron, migración interna), `frontend` debe ser un array vacío [].

Archivos disponibles del codebase (whitelist exhaustiva — NO puedes citar nada fuera de esta lista):
{available_file_paths_formatted}\
"""

# Dynamic portion: per-request context + per-retry warnings + output schema.
_STORY_DYNAMIC_TEMPLATE = """\
{hallucination_warning}{quality_warning}{entity_creation_instruction}
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

Genera ÚNICAMENTE un JSON válido con estos campos exactos:
- title: string corto y descriptivo (máximo 80 caracteres)
- story_description: string en formato de historia de usuario estándar: "Como [tipo de usuario], quiero [acción] para que [beneficio]". Usa el mismo idioma que el texto del requerimiento.
- acceptance_criteria: array de strings en formato Given/When/Then (regla 5). Mínimo 3.
- subtasks: objeto con tres claves obligatorias ("frontend", "backend", "configuration"). Cada una es un array de objetos con dos claves: "title" y "description".
    * "title": string ≤150 caracteres, en imperativo, accionable. Describe la INTENCIÓN de la tarea SIN prefijo de categoría y SIN repetir la ruta de archivo. Ej: "Agregar campo descripción al ProductReadModelMapper".
    * "description": string multilínea (usa "\\n\\n" entre párrafos). Debe explicar: (1) QUÉ hacer en detalle, paso a paso si es necesario; (2) POR QUÉ es necesario o cómo conecta con la historia; (3) qué archivos del whitelist tocar (lista los paths exactos), o si es UI nueva qué componente/pantalla crear sin path concreto; (4) cómo verificarlo (qué tests correr, qué comportamiento observar). Mínimo 30 caracteres.
    * "frontend": ver regla 6. Vacío [] si la historia no tiene UI.
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


_LANGUAGE_NAMES = {
    "es": "español", "en": "English", "fr": "français",
    "de": "Deutsch", "pt": "português",
}


_AC_REPAIR_TEMPLATE = """\
Eres un Product Owner ágil. Recibes una historia cuyos criterios de aceptación fueron rechazados y debes reescribirlos.

Historia:
- Título: {title}
- Descripción: {story_description}

Criterios de aceptación actuales (rechazados):
{current_ac_bulleted}

Motivo del rechazo:
{reason}

Reescribe los {n_ac} criterios de aceptación en lenguaje 100% de Product Owner, generando la salida en {language}:
- Cada AC en formato Given/When/Then ("Dado/Cuando/Entonces" si el idioma es español; equivalentes en otros idiomas).
- Resultado observable por el usuario en términos de negocio.
- PROHIBIDO en los AC: rutas o nombres de archivo, códigos HTTP (201/404/...), métodos REST (POST/GET/...), endpoints (/api/..., /v1/...), nombres de clases/módulos/funciones/tablas/columnas, librerías o frameworks.
- PERMITIDO: nombres visibles de UI (p. ej. "botón 'Crear cuenta'", "mensaje 'Cuenta creada'"), tiempos perceptibles ("en menos de 2 segundos"), reglas de negocio ("contraseña de al menos 8 caracteres").

Responde ÚNICAMENTE con JSON válido, sin texto adicional:
{{"acceptance_criteria": ["AC 1...", "AC 2...", "AC 3..."]}}\
"""


class StoryAIProvider(ABC):
    @abstractmethod
    def generate_story(self, context: dict) -> dict:
        ...

    def repair_acceptance_criteria(
        self, story: dict, reason: str, language: str
    ) -> list[str] | None:
        """Mini-prompt to rewrite ONLY the acceptance criteria.

        Returns the new AC list on success, or None if repair is not supported
        or fails — the caller falls back to a full regeneration retry.
        Default implementation returns None; concrete providers override.
        """
        return None

    @staticmethod
    def _build_repair_prompt(story: dict, reason: str, language: str) -> str:
        current = story.get("acceptance_criteria") or []
        bulleted = "\n".join(f"  - {c}" for c in current) or "  (vacío)"
        lang_label = _LANGUAGE_NAMES.get(language, language)
        return _AC_REPAIR_TEMPLATE.format(
            title=story.get("title", ""),
            story_description=str(story.get("story_description", ""))[:300],
            current_ac_bulleted=bulleted,
            reason=reason,
            n_ac=max(3, len(current)),
            language=lang_label,
        )

    @staticmethod
    def _parse_repaired_ac(raw_text: str) -> list[str] | None:
        try:
            parsed = extract_json(raw_text)
        except Exception:
            return None
        if not isinstance(parsed, dict):
            return None
        ac = parsed.get("acceptance_criteria")
        if not isinstance(ac, list) or not ac:
            return None
        cleaned = [str(c).strip() for c in ac if str(c).strip()]
        return cleaned or None

    @property
    def model_name(self) -> str:
        """Resolved model identifier persisted with each generated story."""
        return getattr(self, "_model", None) or "stub"

    def _build_prompt_parts(self, context: dict) -> tuple[str, str]:
        """Returns (static_part, dynamic_part) for use with prompt caching.

        static_part  — rules + full file whitelist; stable across retries, suitable for caching.
        dynamic_part — per-request context, retry warnings, and output schema.
        """
        available = context.get("available_file_paths", [])
        formatted_available = (
            "\n".join(f"  - {p}" for p in available)
            if available
            else "  (whitelist vacía — NO cites ningún archivo en las subtareas)"
        )
        paths = context.get("impacted_file_paths", [])
        formatted_paths = (
            "\n".join(f"  - {p}" for p in paths)
            if paths
            else "  (no hay archivos específicos identificados)"
        )
        hallucinated = context.get("hallucinated_last_attempt") or []
        hallucination_warning = ""
        if hallucinated:
            joined = ", ".join(hallucinated[:20])
            hallucination_warning = (
                "\nATENCIÓN: tu intento anterior incluyó rutas INVENTADAS que NO existen en el codebase: "
                f"{joined}. No vuelvas a usarlas; limita los paths estrictamente al whitelist.\n"
            )
        quality_reason = context.get("quality_warning_reason")
        quality_warning = ""
        if quality_reason:
            quality_warning = (
                "\nATENCIÓN: tu intento anterior fue rechazado por calidad: "
                f"{quality_reason}. Corrige específicamente ese punto en esta nueva respuesta.\n"
            )
        entity_not_found = context.get("entity_not_found", False)
        entity_name = context.get("entity", "")
        entity_creation_instruction = ""
        if entity_not_found and entity_name:
            entity_creation_instruction = (
                f"\nIMPORTANTE: La entidad '{entity_name}' NO existe en el codebase indexado. "
                f"Esta historia DEBE incluir como primera tarea backend la creación completa de "
                f"'{entity_name}' (modelo/clase, repositorio, migración si aplica). "
                f"El resto de tareas asume que '{entity_name}' se creará en esta misma implementación.\n"
            )
        lang_code = context.get("language", "es")
        language_label = _LANGUAGE_NAMES.get(lang_code, lang_code)

        static = _STORY_STATIC_TEMPLATE.format(
            available_file_paths_formatted=formatted_available,
        )
        dynamic = _STORY_DYNAMIC_TEMPLATE.format(
            hallucination_warning=hallucination_warning,
            quality_warning=quality_warning,
            entity_creation_instruction=entity_creation_instruction,
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
            language=language_label,
        )
        return static, dynamic

    def _build_prompt(self, context: dict) -> str:
        static, dynamic = self._build_prompt_parts(context)
        return static + "\n\n" + dynamic


class StubStoryProvider(StoryAIProvider):
    def generate_story(self, context: dict) -> dict:
        return dict(_STUB_STORY_RESPONSE)


class AnthropicStoryProvider(StoryAIProvider):
    def __init__(self, settings: Settings) -> None:
        if _anthropic_lib is None:
            raise ImportError("anthropic package is required")
        # max_retries=0: SDK-level retries are disabled so AIStoryGenerator's retry
        # loop is the single source of truth. Without this the SDK would retry
        # internally on timeout, multiplying the per-attempt wall time by 3×.
        self._client = _anthropic_lib.Anthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            max_retries=0,
        )
        self._model = settings.AI_MODEL or settings.ANTHROPIC_MODEL
        self._timeout = settings.AI_TIMEOUT_SECONDS
        self._max_output_tokens = settings.AI_MAX_OUTPUT_TOKENS

    def generate_story(self, context: dict) -> dict:
        static_part, dynamic_part = self._build_prompt_parts(context)
        # Static block (rules + whitelist) is marked ephemeral so the large file
        # list is served from the prompt cache on quality/hallucination retries.
        response = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_output_tokens,
            temperature=0,
            timeout=self._timeout,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": static_part,
                        "cache_control": {"type": "ephemeral"},
                    },
                    {
                        "type": "text",
                        "text": dynamic_part,
                    },
                ],
            }],
        )
        log_token_usage(_logger, provider="anthropic", operation="story_gen", model=self._model, response=response)
        if getattr(response, "stop_reason", None) == "max_tokens":
            raise ValueError(
                f"Anthropic response truncated at max_tokens={self._max_output_tokens}; "
                "increase AI_MAX_OUTPUT_TOKENS"
            )
        raw_text = response.content[0].text
        return extract_json(raw_text)

    def repair_acceptance_criteria(
        self, story: dict, reason: str, language: str
    ) -> list[str] | None:
        prompt = self._build_repair_prompt(story, reason, language)
        response = self._client.messages.create(
            model=self._model,
            max_tokens=800,
            temperature=0,
            timeout=self._timeout,
            messages=[{"role": "user", "content": prompt}],
        )
        log_token_usage(
            _logger, provider="anthropic", operation="ac_repair",
            model=self._model, response=response,
        )
        if not response.content:
            return None
        return self._parse_repaired_ac(response.content[0].text)


class OpenAIStoryProvider(StoryAIProvider):
    def __init__(
        self,
        settings: Settings,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        default_model: str = "gpt-4o-mini",
        provider_name: str = "openai",
    ) -> None:
        if _openai_lib is None:
            raise ImportError("openai package is required")
        self._client = _openai_lib.OpenAI(
            api_key=api_key or settings.OPENAI_API_KEY,
            base_url=base_url,
        )
        self._model = settings.AI_MODEL or default_model
        self._timeout = settings.AI_TIMEOUT_SECONDS
        self._max_output_tokens = settings.AI_MAX_OUTPUT_TOKENS
        self._provider_name = provider_name

    def generate_story(self, context: dict) -> dict:
        prompt = self._build_prompt(context)
        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=self._max_output_tokens,
            temperature=0,
            timeout=self._timeout,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
        )
        log_token_usage(
            _logger,
            provider=self._provider_name,
            operation="story_gen",
            model=self._model,
            response=response,
        )
        choice = response.choices[0]
        if getattr(choice, "finish_reason", None) == "length":
            raise ValueError(
                f"OpenAI response truncated at max_tokens={self._max_output_tokens}; "
                "increase AI_MAX_OUTPUT_TOKENS"
            )
        raw_text = choice.message.content
        return extract_json(raw_text)

    def repair_acceptance_criteria(
        self, story: dict, reason: str, language: str
    ) -> list[str] | None:
        prompt = self._build_repair_prompt(story, reason, language)
        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=800,
            temperature=0,
            timeout=self._timeout,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
        )
        log_token_usage(
            _logger, provider=self._provider_name, operation="ac_repair",
            model=self._model, response=response,
        )
        if not response.choices:
            return None
        return self._parse_repaired_ac(response.choices[0].message.content or "")


_GEMINI_CACHE_LOCK = threading.Lock()
# Process-wide index keyed by (model, sha256_short(static_part)) → (cache_name, expires_at_ts).
# Same-whitelist back-to-back calls reuse the explicit cache; different whitelists get
# their own cache entry. Negative numbers / 0 TTL disable caching entirely.
_GEMINI_CACHE_INDEX: dict[tuple[str, str], tuple[str, float]] = {}


class GeminiStoryProvider(StoryAIProvider):
    def __init__(self, settings: Settings) -> None:
        if _genai_lib is None:
            raise ImportError("google-genai package is required")
        self._client = _genai_lib.Client(api_key=settings.GEMINI_API_KEY)
        self._model = settings.AI_MODEL or settings.GEMINI_MODEL
        self._max_output_tokens = settings.AI_MAX_OUTPUT_TOKENS
        ttl_raw = getattr(settings, "GEMINI_CACHE_TTL_SECONDS", 0)
        try:
            self._cache_ttl_seconds = int(ttl_raw or 0)
        except (TypeError, ValueError):
            self._cache_ttl_seconds = 0

    @staticmethod
    def _hash_static(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _is_cache_error(exc: Exception) -> bool:
        msg = str(exc).lower()
        return "cach" in msg or "404" in msg or "not found" in msg

    def _get_or_create_cache(self, static_part: str) -> str | None:
        """Return a usable cache name for the given static block, or None on failure.

        Failures (model min size not met, transient API errors, etc.) downgrade to
        an uncached call rather than breaking story generation.
        """
        if self._cache_ttl_seconds <= 0:
            return None
        key = (self._model, self._hash_static(static_part))
        now = time.time()
        with _GEMINI_CACHE_LOCK:
            entry = _GEMINI_CACHE_INDEX.get(key)
            if entry and entry[1] > now:
                return entry[0]
        try:
            cache = self._client.caches.create(
                model=self._model,
                config=_genai_types.CreateCachedContentConfig(
                    contents=[static_part],
                    ttl=f"{self._cache_ttl_seconds}s",
                ),
            )
        except Exception as exc:  # min size, quota, transient — never break the request path
            _logger.warning(
                "Gemini caches.create failed (model=%s); falling back to uncached: %s",
                self._model, exc,
            )
            return None
        cache_name = getattr(cache, "name", None)
        if not cache_name:
            return None
        # Local expiry has a margin so we never use a cache that's about to expire server-side.
        local_expires = now + max(60, self._cache_ttl_seconds - 30)
        with _GEMINI_CACHE_LOCK:
            _GEMINI_CACHE_INDEX[key] = (cache_name, local_expires)
        return cache_name

    def _invalidate_cache(self, static_part: str) -> None:
        key = (self._model, self._hash_static(static_part))
        with _GEMINI_CACHE_LOCK:
            _GEMINI_CACHE_INDEX.pop(key, None)

    def _generate_content(self, *, cache_name: str | None, static_part: str, dynamic_part: str):
        config_kwargs = {
            "temperature": 0,
            "max_output_tokens": self._max_output_tokens,
            "response_mime_type": "application/json",
            "thinking_config": _genai_types.ThinkingConfig(thinking_budget=0),
        }
        if cache_name:
            config_kwargs["cached_content"] = cache_name
            contents = dynamic_part
        else:
            contents = static_part + "\n\n" + dynamic_part
        return self._client.models.generate_content(
            model=self._model,
            contents=contents,
            config=_genai_types.GenerateContentConfig(**config_kwargs),
        )

    def generate_story(self, context: dict) -> dict:
        static_part, dynamic_part = self._build_prompt_parts(context)
        cache_name = self._get_or_create_cache(static_part)
        try:
            response = self._generate_content(
                cache_name=cache_name, static_part=static_part, dynamic_part=dynamic_part,
            )
        except Exception as exc:
            # Cache may have been GC'd or expired server-side. One-shot retry uncached.
            if cache_name and self._is_cache_error(exc):
                _logger.warning(
                    "Gemini cached call failed; invalidating and retrying uncached: %s", exc,
                )
                self._invalidate_cache(static_part)
                response = self._generate_content(
                    cache_name=None, static_part=static_part, dynamic_part=dynamic_part,
                )
            else:
                raise
        log_token_usage(
            _logger,
            provider="gemini",
            operation="story_gen",
            model=self._model,
            response=response,
        )
        if response.candidates[0].finish_reason.name == "MAX_TOKENS":
            raise ValueError(
                f"Gemini response truncated at max_tokens={self._max_output_tokens}; "
                "increase AI_MAX_OUTPUT_TOKENS"
            )
        return extract_json(response.text)

    def repair_acceptance_criteria(
        self, story: dict, reason: str, language: str
    ) -> list[str] | None:
        prompt = self._build_repair_prompt(story, reason, language)
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=_genai_types.GenerateContentConfig(
                temperature=0,
                max_output_tokens=800,
                response_mime_type="application/json",
                thinking_config=_genai_types.ThinkingConfig(thinking_budget=0),
            ),
        )
        log_token_usage(
            _logger, provider="gemini", operation="ac_repair",
            model=self._model, response=response,
        )
        text = getattr(response, "text", None)
        if not text:
            return None
        return self._parse_repaired_ac(text)


def get_story_ai_provider(settings: Settings) -> StoryAIProvider:
    key = settings.AI_PROVIDER
    if key not in _provider_cache:
        if key == "anthropic":
            _provider_cache[key] = AnthropicStoryProvider(settings)
        elif key == "openai":
            _provider_cache[key] = OpenAIStoryProvider(settings, default_model=settings.OPENAI_MODEL)
        elif key == "groq":
            _provider_cache[key] = OpenAIStoryProvider(
                settings,
                api_key=settings.GROQ_API_KEY,
                base_url=settings.GROQ_BASE_URL,
                default_model=settings.GROQ_MODEL,
                provider_name="groq",
            )
        elif key == "gemini":
            _provider_cache[key] = GeminiStoryProvider(settings)
        else:
            _provider_cache[key] = StubStoryProvider()
    return _provider_cache[key]
