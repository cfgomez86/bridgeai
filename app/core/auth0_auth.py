import logging

import jwt
from fastapi import HTTPException, Request, status
from jwt import PyJWKClient

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_jwks_client: PyJWKClient | None = None


def _get_jwks_client(domain: str) -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(
            f"https://{domain}/.well-known/jwks.json",
            cache_keys=True,
            max_cached_keys=16,
        )
    return _jwks_client


def _extract_bearer_token(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )
    return auth.removeprefix("Bearer ")


def verify_auth0_jwt(token: str) -> dict:
    """Validate an Auth0 JWT and return its payload.

    PyJWKClient fetches JWKS on first call, caches keys, and automatically
    refreshes when the token's kid is not in the cache (key rotation).
    """
    settings = get_settings()
    try:
        client = _get_jwks_client(settings.AUTH0_DOMAIN)
        signing_key = client.get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.AUTH0_AUDIENCE,
            issuer=f"https://{settings.AUTH0_DOMAIN}/",
        )
    except jwt.exceptions.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        )
    except Exception:
        logger.exception("Unexpected error during token verification")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token verification failed.",
        )
