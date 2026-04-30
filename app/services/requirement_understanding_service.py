import hashlib
import json
import re
import uuid
from datetime import datetime, timezone

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.domain.requirement_understanding import RequirementUnderstanding
from app.repositories.requirement_repository import RequirementRepository
from app.services.ai_requirement_parser import AIRequirementParser

_MAX_REQUIREMENT_LENGTH = 2000
_INJECTION_PATTERNS = [r"ignore previous", r"system:", r"<\|", r"\|\|"]


class RequirementUnderstandingService:
    def __init__(
        self,
        ai_parser: AIRequirementParser,
        repo: RequirementRepository,
        settings: Settings = None,
    ) -> None:
        self._parser = ai_parser
        self._repo = repo
        self._settings = settings or get_settings()
        self._logger = get_logger(__name__)

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
            )

        self._logger.info("Processing requirement: %.100s", requirement_text)
        start = datetime.now(timezone.utc)

        parsed = self._parser.parse(requirement_text)

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
        )
