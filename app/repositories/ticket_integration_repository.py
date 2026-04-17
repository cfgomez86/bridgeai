from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.ticket_integration import IntegrationAuditLog, TicketIntegration


class TicketIntegrationRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_story_and_provider(
        self, story_id: str, provider: str
    ) -> Optional[TicketIntegration]:
        return (
            self._db.query(TicketIntegration)
            .filter(
                TicketIntegration.story_id == story_id,
                TicketIntegration.provider == provider,
                TicketIntegration.status == "CREATED",
            )
            .first()
        )

    def save(self, integration: TicketIntegration) -> TicketIntegration:
        self._db.add(integration)
        self._db.commit()
        self._db.refresh(integration)
        return integration

    def update_status(
        self,
        integration_id: str,
        status: str,
        external_ticket_id: Optional[str] = None,
        error_message: Optional[str] = None,
        retry_count: Optional[int] = None,
    ) -> Optional[TicketIntegration]:
        integration = self._db.get(TicketIntegration, integration_id)
        if not integration:
            return None

        integration.status = status
        integration.updated_at = datetime.now(timezone.utc)
        if external_ticket_id is not None:
            integration.external_ticket_id = external_ticket_id
        if error_message is not None:
            integration.error_message = error_message
        if retry_count is not None:
            integration.retry_count = retry_count

        self._db.commit()
        self._db.refresh(integration)
        return integration

    def find_all_by_story_id(self, story_id: str) -> list[TicketIntegration]:
        return (
            self._db.query(TicketIntegration)
            .filter(TicketIntegration.story_id == story_id)
            .order_by(TicketIntegration.created_at.desc())
            .all()
        )

    def get_audit_logs(self, story_id: str) -> list[IntegrationAuditLog]:
        return (
            self._db.query(IntegrationAuditLog)
            .filter(IntegrationAuditLog.story_id == story_id)
            .order_by(IntegrationAuditLog.timestamp.desc())
            .all()
        )

    def add_audit_log(self, log: IntegrationAuditLog) -> None:
        self._db.add(log)
        self._db.commit()
