from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from fastapi import Depends

from app.api.routes import health as health_router
from app.api.routes import indexing as indexing_router
from app.api.routes import impact_analysis as impact_analysis_router
from app.api.routes import understand_requirement as understand_requirement_router
from app.api.routes import story_generation as story_generation_router
from app.api.routes import ticket_integration as ticket_integration_router
from app.api.routes import connections as connections_router
from app.api.routes import auth as auth_router
from app.core.clerk_auth import get_current_user
from app.core.config import get_settings
from app.core.logging import RequestLoggingMiddleware, configure_logging
from app.core.security import SecurityMiddleware, add_cors
import app.models  # noqa: F401 — registers ORM models with Base.metadata


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    configure_logging()
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="BridgeAI",
        description="AI-powered code analysis and User Story generation",
        version="0.1.0",
        lifespan=lifespan,
    )

    # ProxyHeadersMiddleware reads X-Forwarded-* headers to reconstruct the real
    # external URL. Restricted to localhost/loopback — the only legitimate proxy
    # in both dev (Next.js rewrite) and tunnel scenarios.
    trusted_proxies = [h.strip() for h in settings.TRUSTED_PROXY_IPS.split(",") if h.strip()]
    app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=trusted_proxies)

    # Order matters: CORS → Security → Logging
    add_cors(app)
    app.add_middleware(SecurityMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    # Centralised error handler
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error."},
        )

    _auth = [Depends(get_current_user)]

    # Routers — health y auth son públicos; el resto requiere JWT de Clerk
    app.include_router(health_router.router)
    app.include_router(auth_router.router, prefix="/api/v1")
    app.include_router(indexing_router.router, prefix="/api/v1", tags=["indexing"], dependencies=_auth)
    app.include_router(impact_analysis_router.router, prefix="/api/v1", tags=["impact-analysis"], dependencies=_auth)
    app.include_router(understand_requirement_router.router, prefix="/api/v1", tags=["requirement-understanding"], dependencies=_auth)
    app.include_router(story_generation_router.router, prefix="/api/v1", tags=["story-generation"], dependencies=_auth)
    app.include_router(ticket_integration_router.router, prefix="/api/v1", tags=["ticket-integration"], dependencies=_auth)
    # connections: el callback de OAuth es llamado por plataformas externas (sin JWT),
    # por eso el auth se aplica por endpoint dentro del router, no aquí.
    app.include_router(connections_router.router, prefix="/api/v1", tags=["connections"])

    return app


app = create_app()
