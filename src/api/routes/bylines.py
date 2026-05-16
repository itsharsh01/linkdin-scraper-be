from datetime import date
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from src.db.mongo import get_database
from src.schemas.byline import BylineListItem, BylineListResponse
from src.services.byline_query import list_bylines_for_user_on_date

router = APIRouter(prefix="/users", tags=["bylines"])


def _ensure_user_exists(user_id: UUID) -> None:
    database = get_database()
    if database["users"].find_one({"user_id": str(user_id)}) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found for the provided user_id.",
        )


@router.get("/{user_id}/bylines", response_model=BylineListResponse)
def get_bylines_for_user_on_date(
    user_id: UUID,
    date: date = Query(..., description="Calendar day (YYYY-MM-DD) in SCHEDULER_TIMEZONE."),
) -> BylineListResponse:
    _ensure_user_exists(user_id)
    rows = list_bylines_for_user_on_date(user_id, date)
    items = [BylineListItem(**row) for row in rows]
    return BylineListResponse(
        user_id=user_id,
        date=date.isoformat(),
        count=len(items),
        items=items,
    )
