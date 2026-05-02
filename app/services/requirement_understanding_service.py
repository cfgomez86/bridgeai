import hashlib
import json
import re
import uuid
from datetime import datetime, timezone

from app.core.config import Settings, get_settings
from app.core.context import get_user_id
from app.core.logging import get_logger
from app.domain.requirement_understanding import RequirementUnderstanding
from app.repositories.incoherent_requirement_repository import IncoherentRequirementRepository
from app.repositories.requirement_repository import RequirementRepository
from app.services.ai_requirement_parser import AIRequirementParser
from app.services.requirement_coherence_validator import (
    IncoherentRequirementError,
    RequirementCoherenceValidator,
)
from app.services.requirement_gibberish_filter import is_gibberish

_MAX_REQUIREMENT_LENGTH = 2000
_INJECTION_PATTERNS = [r"ignore previous", r"system:", r"<\|", r"\|\|"]

_GIBBERISH_WARNING = (
    "El texto no parece describir una funcionalidad. "
    "Reformula brevemente qué quieres construir."
)
_INVALID_INTENT_WARNING = (
    "El requerimiento no es accionable. "
    "Describe qué cambio o funcionalidad quieres en el sistema."
)
_INVALID_INTENT_MARKERS = {
    "invalid_requirement",
    "invalid",
    "unintelligible",
    "incoherent",
    "none",
    "unknown",
    "n/a",
    "na",
}


class RequirementUnderstandingService:
    def __init__(
        self,
        ai_parser: AIRequirementParser,
        repo: RequirementRepository,
        settings: Settings = None,
        coherence_validator: RequirementCoherenceValidator | None = None,
        incoherent_repo: IncoherentRequirementRepository | None = None,
    ) -> None:
        self._parser = ai_parser
        self._repo = repo
        self._settings = settings or get_settings()
        self._coherence_validator = coherence_validator
        self._incoherent_repo = incoherent_repo
        self._logger = get_logger(__name__)

    @property
    def parser_model_name(self) -> str:
        return self._parser.model_name

    @property
    def coherence_model_name(self) -> str | None:
        if not self._settings.COHERENCE_VALIDATION_ENABLED:
            return None
        if self._coherence_validator is None:
            return None
        return getattr(self._coherence_validator, "model_name", None) or None

    def understand(
        self, requirement_text: str, project_id: str, source_connection_id: str
    ) -> RequirementUnderstanding:
        if not requirement_text or not requirement_text.strip():
            raise ValueError("Requirement text cannot be empty")
        if len(requirement_text) > _MAX_REQUIREMENT_LENGTH:
            raise ValueError(f"Requirement text exceeds maximum length of {_MAX_REQUIREMENT_LENGTH} characters")
        for pattern in _INJECTION_PATTERNS:
            if re.search(pattern, requirement_text, re.IGNORECASE):
                raise ValueError("Requirement contains disallowed patterns")
        if not source_connection_id:
            raise ValueError("source_connection_id is required")

        # Pre-filtro determinístico: detecta texto random ("sddssdds...", "fghfgh") sin
        # tocar al juez LLM. Captura el caso en que gemini-2.5-flash de forma inconsistente
        # acepta basura como coherente.
        if self._settings.COHERENCE_VALIDATION_ENABLED and is_gibberish(requirement_text):
            self._logger.info(
                "Requirement rejected by gibberish pre-filter: text=%.100s",
                requirement_text,
            )
            self._persist_incoherent(
                requirement_text=requirement_text,
                project_id=project_id,
                source_connection_id=source_connection_id,
                warning=_GIBBERISH_WARNING,
                reason_codes=["unintelligible"],
                model_used="deterministic_gibberish_filter",
            )
            raise IncoherentRequirementError(
                warning=_GIBBERISH_WARNING,
                reason_codes=["unintelligible"],
                model_used="deterministic_gibberish_filter",
            )

        # Coherence pre-filter: bloquea requerimientos absurdos antes de gastar tokens
        # en el parser principal y antes de mirar el cache (un texto rechazado nunca debe
        # devolverse desde cache aunque accidentalmente compartiera hash con uno válido).
        coherence_calls = 0
        coherence_model: str | None = None
        if self._settings.COHERENCE_VALIDATION_ENABLED and self._coherence_validator is not None:
            coherence_model = getattr(self._coherence_validator, "model_name", None) or None
            try:
                coherence_calls = 1
                coherence = self._coherence_validator.validate(requirement_text)
            except Exception as exc:
                # Fail-open intencional: una caída del validator (red, timeout, JSON
                # malformado) no bloquea al usuario. El gibberish filter determinístico
                # ya corrió antes y no falla; el parser principal actúa como segunda
                # barrera. Un bypass completo requiere fallar ambas capas, por lo que el
                # riesgo residual es bajo. Mitigación recomendada: rate-limit en el API
                # gateway por tenant, independiente de este validador.
                self._logger.warning("Coherence validator failed (fail-open): %s", exc)
            else:
                if not coherence.is_coherent:
                    self._logger.info(
                        "Requirement rejected by coherence pre-filter: codes=%s text=%.100s",
                        coherence.reason_codes, requirement_text,
                    )
                    self._persist_incoherent(
                        requirement_text=requirement_text,
                        project_id=project_id,
                        source_connection_id=source_connection_id,
                        warning=coherence.warning,
                        reason_codes=coherence.reason_codes,
                        model_used=getattr(
                            self._coherence_validator, "model_name", None
                        ),
                    )
                    raise IncoherentRequirementError(
                        warning=coherence.warning or "El requerimiento no es accionable.",
                        reason_codes=coherence.reason_codes,
                        model_used=getattr(self._coherence_validator, "model_name", None),
                    )

        text_hash = hashlib.sha256(requirement_text.encode()).hexdigest()
        cached = self._repo.find_by_text_project_and_connection(
            text_hash, project_id, source_connection_id
        )
        if cached:
            self._logger.info(
                "Cache hit for requirement hash=%s project=%s connection=%s",
                text_hash[:8], project_id, source_connection_id,
            )
            return RequirementUnderstanding(
                requirement_id=cached.id,
                requirement_text=cached.requirement_text,
                project_id=cached.project_id,
                intent=cached.intent,
                action=cached.action,
                entity=cached.entity,
                feature_type=cached.feature_type,
                priority=cached.priority,
                business_domain=cached.business_domain,
                technical_scope=cached.technical_scope,
                estimated_complexity=cached.estimated_complexity,
                keywords=json.loads(cached.keywords),
                created_at=cached.created_at,
                processing_time_seconds=cached.processing_time_seconds,
                coherence_model=getattr(cached, "coherence_model", None),
                coherence_calls=getattr(cached, "coherence_calls", 0) or 0,
                parser_model=getattr(cached, "parser_model", None),
                parser_calls=getattr(cached, "parser_calls", 0) or 0,
            )

        self._logger.info("Processing requirement: %.100s", requirement_text)
        start = datetime.now(timezone.utc)

        parsed = self._parser.parse(requirement_text)
        # Defensive: tests mock the parser without instrumenting last_call_count
        # or model_name; only persist if the value is the expected primitive type.
        raw_calls = getattr(self._parser, "last_call_count", 1)
        parser_calls = raw_calls if isinstance(raw_calls, int) else 1
        raw_model = getattr(self._parser, "model_name", "")
        parser_model = raw_model if isinstance(raw_model, str) and raw_model else None

        # Segunda barrera: el parser principal a veces detecta gibberish que el juez
        # dejó pasar y devuelve intent="invalid_requirement". Si llega aquí, no
        # persistimos el requirement válido — lo registramos como incoherente.
        intent_marker = (parsed.get("intent") or "").strip().lower()
        if intent_marker in _INVALID_INTENT_MARKERS:
            self._logger.info(
                "Requirement rejected by parser invalid-intent marker: intent=%s text=%.100s",
                intent_marker, requirement_text,
            )
            self._persist_incoherent(
                requirement_text=requirement_text,
                project_id=project_id,
                source_connection_id=source_connection_id,
                warning=_INVALID_INTENT_WARNING,
                reason_codes=["unintelligible"],
                model_used="ai_requirement_parser",
            )
            raise IncoherentRequirementError(
                warning=_INVALID_INTENT_WARNING,
                reason_codes=["unintelligible"],
                model_used="ai_requirement_parser",
            )

        processing_time = (datetime.now(timezone.utc) - start).total_seconds()
        requirement_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc)

        self._repo.save({
            "id": requirement_id,
            "requirement_text": requirement_text,
            "requirement_text_hash": text_hash,
            "project_id": project_id,
            "intent": parsed["intent"],
            "action": parsed["action"],
            "entity": parsed["entity"],
            "feature_type": parsed["feature_type"],
            "priority": parsed["priority"],
            "business_domain": parsed["business_domain"],
            "technical_scope": parsed["technical_scope"],
            "estimated_complexity": parsed["estimated_complexity"],
            "keywords": json.dumps(parsed["keywords"]),
            "processing_time_seconds": processing_time,
            "coherence_model": coherence_model,
            "coherence_calls": coherence_calls,
            "parser_model": parser_model,
            "parser_calls": parser_calls,
            "created_at": created_at,
        }, source_connection_id)
        self._logger.info("Requirement persisted with id=%s in %.3fs", requirement_id, processing_time)

        return RequirementUnderstanding(
            requirement_id=requirement_id,
            requirement_text=requirement_text,
            project_id=project_id,
            intent=parsed["intent"],
            action=parsed["action"],
            entity=parsed["entity"],
            feature_type=parsed["feature_type"],
            priority=parsed["priority"],
            business_domain=parsed["business_domain"],
            technical_scope=parsed["technical_scope"],
            estimated_complexity=parsed["estimated_complexity"],
            keywords=parsed["keywords"],
            created_at=created_at,
            processing_time_seconds=processing_time,
            coherence_model=coherence_model,
            coherence_calls=coherence_calls,
            parser_model=parser_model,
            parser_calls=parser_calls,
        )

    def _persist_incoherent(
        self,
        requirement_text: str,
        project_id: str,
        source_connection_id: str,
        warning: str | None,
        reason_codes: list[str],
        model_used: str | None,
    ) -> None:
        if self._incoherent_repo is None:
            return
        try:
            self._incoherent_repo.save({
                "id": str(uuid.uuid4()),
                "user_id": get_user_id(),
                "requirement_text": requirement_text,
                "requirement_text_hash": hashlib.sha256(
                    requirement_text.encode()
                ).hexdigest(),
                "warning": warning,
                "reason_codes": json.dumps(reason_codes),
                "project_id": project_id,
                "source_connection_id": source_connection_id,
                "model_used": model_used,
            })
        except Exception as persist_exc:
            self._logger.error(
                "Failed to persist incoherent requirement: %s", persist_exc
            )
