from fastapi import APIRouter, HTTPException

from core.config import settings
from db.mongo import ping_database

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health_check() -> dict[str, str]:
    try:
        ping_database()
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "database": "unreachable",
                "message": str(exc),
            },
        ) from exc

    return {
        "status": "ok",
        "database": "connected",
        "db_name": settings.db_name,
    }
