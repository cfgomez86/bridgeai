from collections.abc import Callable

from fastapi import Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# 10 MB request body limit
MAX_CONTENT_LENGTH: int = 10 * 1024 * 1024

SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}


class SecurityMiddleware(BaseHTTPMiddleware):
    """Validates Content-Type, enforces request size limit, and injects security headers."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Enforce request body size limit
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_CONTENT_LENGTH:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={"detail": "Request body too large."},
            )

        # Validate Content-Type for mutation requests
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

        return response


def add_cors(app) -> None:  # type: ignore[no-untyped-def]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
