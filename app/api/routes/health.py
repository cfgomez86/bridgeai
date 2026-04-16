from fastapi import APIRouter, Request

from app.database.session import check_db_connection

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(request: Request) -> dict[str, str]:
    db_ok = check_db_connection()
    request_id: str = getattr(request.state, "request_id", "unknown")

    return {
        "status": "ok",
        "database": "connected" if db_ok else "unavailable",
        "request_id": request_id,
    }
