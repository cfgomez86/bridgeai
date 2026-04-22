from collections.abc import Callable

from fastapi import Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings

# 10 MB request body limit
MAX_CONTENT_LENGTH: int = 10 * 1024 * 1024

# Headers applied on all responses. HSTS is applied separately, only over HTTPS.
SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}


class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_CONTENT_LENGTH:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={"detail": "Request body too large."},
            )

        if request.method in {"POST", "PUT", "PATCH"}:
            content_type = request.headers.get("content-type", "")
            if not content_type.startswith("application/json"):
                return JSONResponse(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    content={"detail": "Content-Type must be application/json."},
                )

        response = await call_next(request)

        for header, value in SECURITY_HEADERS.items():
            response.headers[header] = value

        # HSTS only over HTTPS — avoids poisoning browsers on HTTP local dev,
        # and omits includeSubDomains since devtunnel subdomains are not ours.
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000"

        return response


def add_cors(app) -> None:  # type: ignore[no-untyped-def]
    settings = get_settings()
    origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]

    if not origins:
        raise RuntimeError(
            "CORS_ORIGINS must not be empty. Set it in your .env or .env.{APP_ENV} file."
        )
    if origins == ["*"]:
        raise RuntimeError(
            "CORS_ORIGINS='*' is incompatible with allow_credentials=True. List explicit origins."
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
