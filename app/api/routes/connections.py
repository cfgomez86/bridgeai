import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings

SUPPORTED_PLATFORMS_SET = {"github", "gitlab", "azure_devops"}
from app.database.session import get_db
from app.repositories.source_connection_repository import SourceConnectionRepository
from app.services.source_connection_service import SourceConnectionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/connections", tags=["connections"])


# ── Dependency ──────────────────────────────────────────────────────────────

def get_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SourceConnectionService:
    return SourceConnectionService(SourceConnectionRepository(db), settings)


# ── Schemas ──────────────────────────────────────────────────────────────────

class PlatformConfigRequest(BaseModel):
    client_id: str
    client_secret: str


class PlatformResponse(BaseModel):
    platform: str
    label: str
    configured: bool
    client_id: str | None
    server_configured: bool = False
    redirect_uri: str | None = None


class ConnectionResponse(BaseModel):
    id: str
    platform: str
    display_name: str
    repo_full_name: str | None
    repo_name: str | None
    owner: str | None
    default_branch: str
    is_active: bool


class RepoResponse(BaseModel):
    full_name: str
    name: str
    owner: str
    default_branch: str
    private: bool


class ActivateRequest(BaseModel):
    repo_full_name: str
    default_branch: str = "main"


# ── Platform config endpoints ────────────────────────────────────────────────

@router.get("/platforms", response_model=list[PlatformResponse])
def list_platforms(service: SourceConnectionService = Depends(get_service)):
    return service.list_platforms()


@router.put("/platforms/{platform}", response_model=PlatformResponse)
def save_platform_config(
    platform: str,
    body: PlatformConfigRequest,
    service: SourceConnectionService = Depends(get_service),
):
    try:
        config = service.save_platform_config(platform, body.client_id, body.client_secret)
        platforms = {p["platform"]: p for p in service.list_platforms()}
        p = platforms.get(platform, {})
        return {
            "platform": config.platform,
            "label": p.get("label", platform),
            "configured": True,
            "client_id": config.client_id,
            "server_configured": p.get("server_configured", False),
        }
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.delete("/platforms/{platform}", status_code=status.HTTP_204_NO_CONTENT)
def delete_platform_config(
    platform: str,
    service: SourceConnectionService = Depends(get_service),
):
    deleted = service.delete_platform_config(platform)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Platform {platform!r} not configured")


# ── OAuth flow endpoints ─────────────────────────────────────────────────────

class AuthorizeResponse(BaseModel):
    url: str
    redirect_uri: str


class RedirectUriResponse(BaseModel):
    redirect_uri: str


def _resolve_base(
    origin: str | None,
    request: Request,
    settings: Settings,
) -> str:
    """Return the validated base URL for building redirect_uri.

    The `origin` param comes from window.location.origin in the browser.
    We validate it against CORS_ORIGINS so a malicious actor cannot supply
    an arbitrary redirect destination.
    """
    if origin is None:
        return str(request.base_url).rstrip("/")
    normalized = origin.rstrip("/")
    allowed = {o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()}
    if normalized not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid origin parameter.",
        )
    return normalized


def _require_platform(platform: str) -> str:
    if platform not in SUPPORTED_PLATFORMS_SET:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Platform {platform!r} is not supported.",
        )
    return platform


@router.get("/oauth/redirect-uri/{platform}", response_model=RedirectUriResponse)
def get_redirect_uri(
    platform: str,
    request: Request,
    origin: str | None = Query(None),
    settings: Settings = Depends(get_settings),
):
    _require_platform(platform)
    base = _resolve_base(origin, request, settings)
    return RedirectUriResponse(redirect_uri=f"{base}/api/v1/connections/oauth/callback/{platform}")


@router.get("/oauth/authorize/{platform}", response_model=AuthorizeResponse)
def authorize(
    platform: str,
    request: Request,
    origin: str | None = Query(None),
    service: SourceConnectionService = Depends(get_service),
    settings: Settings = Depends(get_settings),
):
    _require_platform(platform)
    try:
        base = _resolve_base(origin, request, settings)
        redirect_uri = f"{base}/api/v1/connections/oauth/callback/{platform}"
        url = service.get_authorize_url(platform, redirect_uri)
        return AuthorizeResponse(url=url, redirect_uri=redirect_uri)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/oauth/callback/{platform}")
def oauth_callback(
    platform: str,
    code: str,
    state: str,
    service: SourceConnectionService = Depends(get_service),
    settings: Settings = Depends(get_settings),
):
    try:
        service.handle_callback(platform, code, state)
        frontend_url = settings.FRONTEND_URL.rstrip("/")
        return RedirectResponse(url=f"{frontend_url}/connections?connected={platform}")
    except ValueError as exc:
        logger.error("OAuth callback failed platform=%s error=%s", platform, exc)
        frontend_url = settings.FRONTEND_URL.rstrip("/")
        return RedirectResponse(url=f"{frontend_url}/connections?error={platform}")


# ── Connection management endpoints ─────────────────────────────────────────

@router.get("", response_model=list[ConnectionResponse])
def list_connections(service: SourceConnectionService = Depends(get_service)):
    conns = service.list_connections()
    return [
        ConnectionResponse(
            id=c.id,
            platform=c.platform,
            display_name=c.display_name,
            repo_full_name=c.repo_full_name,
            repo_name=c.repo_name,
            owner=c.owner,
            default_branch=c.default_branch,
            is_active=c.is_active,
        )
        for c in conns
    ]


@router.get("/active", response_model=ConnectionResponse | None)
def get_active(service: SourceConnectionService = Depends(get_service)):
    conn = service.get_active_connection()
    if not conn:
        return None
    return ConnectionResponse(
        id=conn.id,
        platform=conn.platform,
        display_name=conn.display_name,
        repo_full_name=conn.repo_full_name,
        repo_name=conn.repo_name,
        owner=conn.owner,
        default_branch=conn.default_branch,
        is_active=conn.is_active,
    )


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_connection(
    connection_id: str,
    service: SourceConnectionService = Depends(get_service),
):
    deleted = service.delete_connection(connection_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found")


@router.get("/{connection_id}/repos", response_model=list[RepoResponse])
def list_repos(
    connection_id: str,
    service: SourceConnectionService = Depends(get_service),
):
    try:
        repos = service.list_repos(connection_id)
        return [
            RepoResponse(
                full_name=r.full_name,
                name=r.name,
                owner=r.owner,
                default_branch=r.default_branch,
                private=r.private,
            )
            for r in repos
        ]
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to list repos connection=%s error=%s", connection_id, exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to fetch repositories from the SCM provider.")


@router.post("/{connection_id}/activate", response_model=ConnectionResponse)
def activate_repo(
    connection_id: str,
    body: ActivateRequest,
    service: SourceConnectionService = Depends(get_service),
):
    try:
        conn = service.activate_repo(connection_id, body.repo_full_name, body.default_branch)
        return ConnectionResponse(
            id=conn.id,
            platform=conn.platform,
            display_name=conn.display_name,
            repo_full_name=conn.repo_full_name,
            repo_name=conn.repo_name,
            owner=conn.owner,
            default_branch=conn.default_branch,
            is_active=conn.is_active,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
