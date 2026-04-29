import logging
import time

import httpx
from fastapi import HTTPException, Request, status
from jose import JWTError, jwt

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_jwks_cache: dict = {}
_jwks_fetched_at: float = 0.0
_JWKS_TTL_SECONDS = 3600


def _fetch_jwks(domain: str) -> dict:
    """Fetch JWKS from Auth0 and return the raw dict."""
    resp = httpx.get(f"https://{domain}/.well-known/jwks.json", timeout=10)
    resp.raise_for_status()
    return resp.json()


def _get_jwks(domain: str) -> dict:
    global _jwks_cache, _jwks_fetched_at
    if time.time() - _jwks_fetched_at > _JWKS_TTL_SECONDS:
        _jwks_cache = _fetch_jwks(domain)
        _jwks_fetched_at = time.time()
    return _jwks_cache


def _get_token_kid(token: str) -> str | None:
    """Extract the `kid` claim from a JWT header without verifying the signature."""
    try:
        header = jwt.get_unverified_header(token)
        return header.get("kid")
    except Exception:
        return None


def _kid_in_jwks(kid: str | None, jwks: dict) -> bool:
    """Return True if the given kid is present in the JWKS key set."""
    if kid is None:
        return True  # No kid — let decode decide
    return any(k.get("kid") == kid for k in jwks.get("keys", []))


def _extract_bearer_token(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )
    return auth.removeprefix("Bearer ")


def verify_auth0_jwt(token: str) -> dict:
    settings = get_settings()
    try:
        jwks = _get_jwks(settings.AUTH0_DOMAIN)

        # If the token's kid is not in the cached JWKS, Auth0 may have rotated
        # keys since last fetch — force a refresh once before failing.
        kid = _get_token_kid(token)
        if not _kid_in_jwks(kid, jwks):
            logger.info("JWKS kid=%s not found in cache — refreshing JWKS", kid)
            global _jwks_cache, _jwks_fetched_at
            _jwks_cache = _fetch_jwks(settings.AUTH0_DOMAIN)
            _jwks_fetched_at = time.time()
            jwks = _jwks_cache

        payload = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            audience=settings.AUTH0_AUDIENCE,
            issuer=f"https://{settings.AUTH0_DOMAIN}/",
        )
        return payload
    except JWTError:
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


