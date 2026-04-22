import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.core.context import current_tenant_id, get_tenant_id
from app.models.ticket_integration import IntegrationAuditLog, TicketIntegration


class TicketIntegrationRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def _tid(self) -> str:
        return get_tenant_id()

    def find_by_story_and_provider(
        self, story_id: str, provider: str
    ) -> Optional[TicketIntegration]:
        return (
            self._db.query(TicketIntegration)
            .filter(
                TicketIntegration.tenant_id == self._tid(),
                TicketIntegration.story_id == story_id,
                TicketIntegration.provider == provider,
                TicketIntegration.status == "CREATED",
            )
            .first()
        )

    def create_integration(
        self,
        story_id: str,
        provider: str,
        project_key: str,
        issue_type: str,
    ) -> str:
        now = datetime.now(timezone.utc)
        integration_id = str(uuid.uuid4())
        model = TicketIntegration(
            id=integration_id,
            tenant_id=self._tid(),
            story_id=story_id,
            provider=provider,
            project_key=project_key,
            issue_type=issue_type,
            external_ticket_id=None,
            status="PENDING",
            retry_count=0,
            error_message=None,
            created_at=now,
            updated_at=now,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return integration_id

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
            .filter(
                TicketIntegration.tenant_id == self._tid(),
                TicketIntegration.story_id == story_id,
            )
            .order_by(TicketIntegration.created_at.desc())
            .all()
        )

    def get_audit_logs(self, story_id: str) -> list[IntegrationAuditLog]:
        return (
            self._db.query(IntegrationAuditLog)
            .filter(
                IntegrationAuditLog.tenant_id == self._tid(),
                IntegrationAuditLog.story_id == story_id,
            )
            .order_by(IntegrationAuditLog.timestamp.desc())
            .all()
        )

    def add_audit_log(
        self,
        story_id: str,
        provider: str,
        action: str,
        payload: str | None,
        response: str | None,
        status: str,
        timestamp: datetime,
    ) -> None:
        log = IntegrationAuditLog(
            id=str(uuid.uuid4()),
            tenant_id=self._tid(),
            story_id=story_id,
            provider=provider,
            action=action,
            payload=payload,
            response=response,
            status=status,
            timestamp=timestamp,
        )
        self._db.add(log)
        self._db.commit()

    def get_latest_subtask_audit(self, story_id: str, provider: str) -> IntegrationAuditLog | None:
        return (
            self._db.query(IntegrationAuditLog)
            .filter(
                IntegrationAuditLog.tenant_id == self._tid(),
                IntegrationAuditLog.story_id == story_id,
                IntegrationAuditLog.provider == provider,
                IntegrationAuditLog.status == "CREATED",
                IntegrationAuditLog.action.in_(["create_ticket", "create_subtasks"]),
            )
            .order_by(IntegrationAuditLog.timestamp.desc())
            .first()
        )
