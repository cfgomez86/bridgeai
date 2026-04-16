import logging
import time
import uuid
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings


def configure_logging() -> None:
    settings = get_settings()
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Attaches a unique request_id and logs each request with timing."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        logger = get_logger("bridgeai.request")
        start = time.perf_counter()

        logger.info(
            "request_start path=%s method=%s request_id=%s",
            request.url.path,
            request.method,
            request_id,
        )

        response = await call_next(request)

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "request_end path=%s method=%s status=%s duration_ms=%.2f request_id=%s",
            request.url.path,
            request.method,
            response.status_code,
            elapsed_ms,
            request_id,
        )

        response.headers["X-Request-ID"] = request_id
        return response
