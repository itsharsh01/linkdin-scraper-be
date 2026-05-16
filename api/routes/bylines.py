from datetime import date
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from db.mongo import get_database
from schemas.byline import (
    BulkBylineStatusUpdateResponse,
    BylineListItem,
    BylineListResponse,
    BylineStatusUpdate,
    BylineStatusUpdateResponse,
)
from services.byline_query import list_bylines_for_user_on_date
from services.byline_status import bulk_set_false_bylines_to_true, update_byline_status

router = APIRouter(prefix="/users", tags=["bylines"])


def _ensure_user_exists(user_id: UUID) -> None:
    database = get_database()
    if database["users"].find_one({"user_id": str(user_id)}) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found for the provided user_id.",
        )


@router.patch(
    "/{user_id}/bylines/bulk-status",
    response_model=BulkBylineStatusUpdateResponse,
    status_code=status.HTTP_200_OK,
)
def bulk_update_byline_status_to_true(user_id: UUID) -> BulkBylineStatusUpdateResponse:
    """
    Set `status=True` on all author bylines for this user where `status` is currently False.
    """
    _ensure_user_exists(user_id)
    try:
        stats = bulk_set_false_bylines_to_true(user_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    return BulkBylineStatusUpdateResponse(user_id=user_id, **stats)


@router.patch(
    "/{user_id}/bylines/{byline_id}/status",
    response_model=BylineStatusUpdateResponse,
    status_code=status.HTTP_200_OK,
)
def update_single_byline_status(
    user_id: UUID,
    byline_id: str,
    payload: BylineStatusUpdate,
) -> BylineStatusUpdateResponse:
    """Update `status` on one author byline (MongoDB document id as `byline_id`)."""
    _ensure_user_exists(user_id)
    try:
        result = update_byline_status(user_id, byline_id, payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return BylineStatusUpdateResponse(**result)


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
