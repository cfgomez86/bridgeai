import asyncio
import uuid
from urllib.error import HTTPError

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.database.session import get_db
from app.services.ticket_integration_service import (
    StoryNotFoundError,
    TicketIntegrationService,
    UnsupportedProviderError,
)

logger = get_logger(__name__)

router = APIRouter(tags=["ticket-integration"])


class TicketStatusResponse(BaseModel):
    integration_id: str
    story_id: str
    provider: str
    project_key: str
    issue_type: str
    external_ticket_id: str | None
    status: str
    retry_count: int
    error_message: str | None
    created_at: str
    updated_at: str


class AuditLogEntry(BaseModel):
    id: str
    story_id: str
    provider: str
    action: str
    payload: str | None
    response: str | None
    status: str
    timestamp: str


class CreateTicketRequest(BaseModel):
    story_id: str
    integration_type: str
    project_key: str
    issue_type: str = "Story"


class CreateTicketResponse(BaseModel):
    ticket_id: str
    url: str
    provider: str
    status: str
    message: str | None = None


def get_integration_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TicketIntegrationService:
    return TicketIntegrationService(db=db, settings=settings)


@router.post("/tickets", response_model=CreateTicketResponse)
async def create_ticket(
    body: CreateTicketRequest,
    request: Request,
    response: Response,
    service: TicketIntegrationService = Depends(get_integration_service),
):
    request_id = str(getattr(request.state, "request_id", uuid.uuid4()))
    logger.info(
        "POST /tickets request_id=%s story_id=%s provider=%s",
        request_id, body.story_id, body.integration_type,
    )

    try:
        result, is_duplicate = await service.create_ticket(
            story_id=body.story_id,
            provider_name=body.integration_type,
            project_key=body.project_key,
            issue_type=body.issue_type,
            request_id=request_id,
        )
    except StoryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except UnsupportedProviderError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except HTTPError as exc:
        retryable = exc.code not in (400, 401, 403)
        jira_body = getattr(exc, "jira_error_body", None)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": f"HTTP {exc.code}: {exc.reason}",
                "provider": body.integration_type,
                "retryable": retryable,
                **({"jira_detail": jira_body} if jira_body else {}),
            },
        )
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error(
            "POST /tickets failed request_id=%s error=%s", request_id, exc
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ticket creation failed: {exc}",
        )

    response.status_code = status.HTTP_200_OK if is_duplicate else status.HTTP_201_CREATED
    return CreateTicketResponse(
        ticket_id=result.external_id,
        url=result.url,
        provider=result.provider,
        status=result.status,
        message="Ticket already exists" if is_duplicate else None,
    )


@router.get("/tickets/{story_id}", response_model=list[TicketStatusResponse])
async def get_ticket_status(
    story_id: str,
    service: TicketIntegrationService = Depends(get_integration_service),
):
    records = await asyncio.to_thread(service.get_integrations, story_id)
    return [
        TicketStatusResponse(
            integration_id=r.id,
            story_id=r.story_id,
            provider=r.provider,
            project_key=r.project_key,
            issue_type=r.issue_type,
            external_ticket_id=r.external_ticket_id,
            status=r.status,
            retry_count=r.retry_count,
            error_message=r.error_message,
            created_at=r.created_at.isoformat(),
            updated_at=r.updated_at.isoformat(),
        )
        for r in records
    ]


@router.get("/tickets/{story_id}/audit", response_model=list[AuditLogEntry])
async def get_ticket_audit(
    story_id: str,
    service: TicketIntegrationService = Depends(get_integration_service),
):
    logs = await asyncio.to_thread(service.get_audit_logs, story_id)
    return [
        AuditLogEntry(
            id=log.id,
            story_id=log.story_id,
            provider=log.provider,
            action=log.action,
            payload=log.payload,
            response=log.response,
            status=log.status,
            timestamp=log.timestamp.isoformat(),
        )
        for log in logs
    ]


@router.get("/integration/health")
async def integration_health(
    service: TicketIntegrationService = Depends(get_integration_service),
):
    return await service.health_check()
