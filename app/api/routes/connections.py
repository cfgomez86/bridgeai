import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth0_auth import get_current_user
from app.core.config import Settings, get_settings
from app.database.session import get_db
from app.models.user import User
from app.repositories.code_file_repository import CodeFileRepository
from app.repositories.source_connection_repository import SourceConnectionRepository
from app.services.source_connection_service import SourceConnectionService

SUPPORTED_PLATFORMS_SET = {"github", "gitlab", "azure_devops", "jira"}
_PAT_SUPPORTED_PLATFORMS = {"github", "gitlab", "azure_devops", "bitbucket", "jira"}

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/connections", tags=["connections"])


# ── Dependency ──────────────────────────────────────────────────────────────

def get_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SourceConnectionService:
    return SourceConnectionService(SourceConnectionRepository(db), settings)


# ── Schemas ──────────────────────────────────────────────────────────────────

class PlatformResponse(BaseModel):
    platform: str
    label: str
    server_configured: bool = False


class ConnectionResponse(BaseModel):
    id: str
    platform: str
    display_name: str
    repo_full_name: str | None
    repo_name: str | None
    owner: str | None
    default_branch: str
    is_active: bool
    boards_project: str | None = None
    auth_method: str = "oauth"


class RepoResponse(BaseModel):
    full_name: str
    name: str
    owner: str
    default_branch: str
    private: bool


class ActivateRequest(BaseModel):
    repo_full_name: str
    default_branch: str = "main"


class PATConnectRequest(BaseModel):
    platform: str
    token: str
    org_url: str | None = None   # Required for Azure DevOps PAT
    base_url: str | None = None  # Required for Jira; optional for GitLab/Bitbucket self-hosted
    email: str | None = None     # Required for Jira API token (Basic Auth)


# ── Platform listing ────────────────────────────────────────────────────────

@router.get("/platforms", response_model=list[PlatformResponse])
def list_platforms(
    service: SourceConnectionService = Depends(get_service),
    _user: User = Depends(get_current_user),
):
    return service.list_platforms()


# ── OAuth flow endpoints ─────────────────────────────────────────────────────

class AuthorizeResponse(BaseModel):
    url: str
    redirect_uri: str


class RedirectUriResponse(BaseModel):
    redirect_uri: str


def _require_platform(platform: str) -> str:
    if platform not in SUPPORTED_PLATFORMS_SET:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Platform {platform!r} is not supported.",
        )
    return platform


def _callback_uri(platform: str, settings: Settings) -> str:
    base = settings.API_BASE_URL.rstrip("/")
    return f"{base}/api/v1/connections/oauth/callback/{platform}"


@router.get("/oauth/redirect-uri/{platform}", response_model=RedirectUriResponse)
def get_redirect_uri(
    platform: str,
    settings: Settings = Depends(get_settings),
    _user: User = Depends(get_current_user),
):
    _require_platform(platform)
    return RedirectUriResponse(redirect_uri=_callback_uri(platform, settings))


@router.get("/oauth/authorize/{platform}", response_model=AuthorizeResponse)
def authorize(
    platform: str,
    service: SourceConnectionService = Depends(get_service),
    settings: Settings = Depends(get_settings),
    _user: User = Depends(get_current_user),
):
    _require_platform(platform)
    try:
        redirect_uri = _callback_uri(platform, settings)
        url = service.get_authorize_url(platform, redirect_uri)
        return AuthorizeResponse(url=url, redirect_uri=redirect_uri)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/oauth/callback/{platform}")
def oauth_callback(
    platform: str,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
    service: SourceConnectionService = Depends(get_service),
    settings: Settings = Depends(get_settings),
):
    frontend_url = settings.FRONTEND_URL.rstrip("/")
    if error or not code or not state:
        desc = error_description or error or "OAuth flow cancelled or failed."
        logger.error("OAuth callback error platform=%s error=%s", platform, desc)
        return RedirectResponse(url=f"{frontend_url}/connections?error={platform}")
    try:
        service.handle_callback(platform, code, state)
        return RedirectResponse(url=f"{frontend_url}/connections?connected={platform}")
    except ValueError as exc:
        logger.error("OAuth callback failed platform=%s error=%s", platform, exc)
        return RedirectResponse(url=f"{frontend_url}/connections?error={platform}")


# ── PAT connection endpoint ─────────────────────────────────────────────────

@router.post("/pat", response_model=ConnectionResponse, status_code=status.HTTP_201_CREATED)
def connect_pat(
    body: PATConnectRequest,
    service: SourceConnectionService = Depends(get_service),
    _user: User = Depends(get_current_user),
):
    if body.platform not in _PAT_SUPPORTED_PLATFORMS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"PAT connections are not supported for platform {body.platform!r}. Supported: {sorted(_PAT_SUPPORTED_PLATFORMS)}",
        )
    try:
        conn = service.create_pat_connection(
            platform=body.platform,
            token=body.token,
            org_url=body.org_url,
            base_url=body.base_url,
            email=body.email,
        )
        return ConnectionResponse(
            id=conn.id,
            platform=conn.platform,
            display_name=conn.display_name,
            repo_full_name=conn.repo_full_name,
            repo_name=conn.repo_name,
            owner=conn.owner,
            default_branch=conn.default_branch,
            is_active=conn.is_active,
            boards_project=conn.boards_project,
            auth_method=conn.auth_method,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        logger.error("PAT connection failed platform=%s error=%s", body.platform, exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="PAT validation failed — check the token and try again.")


# ── Connection management endpoints ─────────────────────────────────────────

@router.get("", response_model=list[ConnectionResponse])
def list_connections(
    service: SourceConnectionService = Depends(get_service),
    _user: User = Depends(get_current_user),
):
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
            boards_project=c.boards_project,
            auth_method=c.auth_method,
        )
        for c in conns
    ]


@router.get("/active", response_model=ConnectionResponse | None)
def get_active(
    service: SourceConnectionService = Depends(get_service),
    _user: User = Depends(get_current_user),
):
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
        boards_project=conn.boards_project,
        auth_method=conn.auth_method,
    )


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_connection(
    connection_id: str,
    service: SourceConnectionService = Depends(get_service),
    _user: User = Depends(get_current_user),
):
    deleted = service.delete_connection(connection_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found")


@router.get("/{connection_id}/repos", response_model=list[RepoResponse])
def list_repos(
    connection_id: str,
    service: SourceConnectionService = Depends(get_service),
    _user: User = Depends(get_current_user),
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
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    try:
        old = SourceConnectionRepository(db).find_by_id(connection_id)
        old_repo = old.repo_full_name if old else None
        # Expunge so service.activate() gets a fresh DB read after the bulk
        # UPDATE (synchronize_session=False wouldn't expire it otherwise, and
        # SQLAlchemy wouldn't detect is_active True→True as a dirty change).
        if old is not None:
            db.expunge(old)

        conn = service.activate_repo(connection_id, body.repo_full_name, body.default_branch)

        # Repo changed → stale index belongs to the old repo; clear it so the user
        # is forced to re-index before running analysis on the new codebase.
        if old_repo and old_repo != body.repo_full_name:
            deleted = CodeFileRepository(db).delete_by_connection(connection_id)
            logger.info(
                "Repo changed connection=%s old=%s new=%s cleared_files=%d",
                connection_id, old_repo, body.repo_full_name, deleted,
            )

        return ConnectionResponse(
            id=conn.id,
            platform=conn.platform,
            display_name=conn.display_name,
            repo_full_name=conn.repo_full_name,
            repo_name=conn.repo_name,
            owner=conn.owner,
            default_branch=conn.default_branch,
            is_active=conn.is_active,
            boards_project=conn.boards_project,
            auth_method=conn.auth_method,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# ── Audit log endpoints ─────────────────────────────────────────────────────

class AuditLogEntry(BaseModel):
    id: str
    connection_id: str
    platform: str
    auth_method: str
    event: str
    actor: str
    detail: str | None
    timestamp: str


@router.get("/audit", response_model=list[AuditLogEntry])
def list_all_audit_logs(
    service: SourceConnectionService = Depends(get_service),
    _user: User = Depends(get_current_user),
):
    return service.list_audit_logs()


@router.get("/{connection_id}/audit", response_model=list[AuditLogEntry])
def list_connection_audit_logs(
    connection_id: str,
    service: SourceConnectionService = Depends(get_service),
    _user: User = Depends(get_current_user),
):
    return service.list_audit_logs(connection_id=connection_id)


# ── Azure Boards project selection ──────────────────────────────────────────

class ActivateBoardsProjectRequest(BaseModel):
    project_full_name: str


@router.post("/{connection_id}/activate-project", response_model=ConnectionResponse)
def activate_boards_project(
    connection_id: str,
    body: ActivateBoardsProjectRequest,
    service: SourceConnectionService = Depends(get_service),
    _user: User = Depends(get_current_user),
):
    try:
        conn = service.activate_boards_project(connection_id, body.project_full_name)
        return ConnectionResponse(
            id=conn.id,
            platform=conn.platform,
            display_name=conn.display_name,
            repo_full_name=conn.repo_full_name,
            repo_name=conn.repo_name,
            owner=conn.owner,
            default_branch=conn.default_branch,
            is_active=conn.is_active,
            boards_project=conn.boards_project,
            auth_method=conn.auth_method,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# ── Jira site selection ──────────────────────────────────────────────────────

class AzureProjectResponse(BaseModel):
    name: str
    org: str
    full_name: str
    process_template: str = ""


@router.get("/{connection_id}/project-process")
def get_project_process(
    connection_id: str,
    project: str,
    service: SourceConnectionService = Depends(get_service),
    _user: User = Depends(get_current_user),
):
    try:
        template = service.get_project_process(connection_id, project)
        return {"process_template": template}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to get project process connection=%s project=%s error=%s", connection_id, project, exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to fetch project process template.")


@router.get("/{connection_id}/projects", response_model=list[AzureProjectResponse])
def list_projects(
    connection_id: str,
    service: SourceConnectionService = Depends(get_service),
    _user: User = Depends(get_current_user),
):
    try:
        projects = service.list_projects(connection_id)
        return [AzureProjectResponse(**p) for p in projects]
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to list projects connection=%s error=%s", connection_id, exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to fetch Azure DevOps projects.")


class JiraSiteResponse(BaseModel):
    id: str
    name: str
    url: str
    api_base_url: str


class JiraProjectResponse(BaseModel):
    key: str
    name: str


@router.get("/{connection_id}/jira-projects", response_model=list[JiraProjectResponse])
def list_jira_projects(
    connection_id: str,
    service: SourceConnectionService = Depends(get_service),
    _user: User = Depends(get_current_user),
):
    try:
        projects = service.list_jira_projects(connection_id)
        return [JiraProjectResponse(**p) for p in projects]
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to list Jira projects connection=%s error=%s", connection_id, exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to fetch Jira projects.")


class ActivateSiteRequest(BaseModel):
    cloud_id: str
    api_base_url: str
    site_url: str
    site_name: str


@router.get("/{connection_id}/sites", response_model=list[JiraSiteResponse])
def list_sites(
    connection_id: str,
    service: SourceConnectionService = Depends(get_service),
    _user: User = Depends(get_current_user),
):
    try:
        sites = service.list_sites(connection_id)
        return [JiraSiteResponse(**s) for s in sites]
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to list Jira sites connection=%s error=%s", connection_id, exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to fetch Jira sites.")


@router.post("/{connection_id}/activate-site", response_model=ConnectionResponse)
def activate_site(
    connection_id: str,
    body: ActivateSiteRequest,
    service: SourceConnectionService = Depends(get_service),
    _user: User = Depends(get_current_user),
):
    try:
        conn = service.activate_site(
            connection_id, body.cloud_id, body.api_base_url, body.site_url, body.site_name
        )
        return ConnectionResponse(
            id=conn.id,
            platform=conn.platform,
            display_name=conn.display_name,
            repo_full_name=conn.repo_full_name,
            repo_name=conn.repo_name,
            owner=conn.owner,
            default_branch=conn.default_branch,
            is_active=conn.is_active,
            boards_project=conn.boards_project,
            auth_method=conn.auth_method,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
