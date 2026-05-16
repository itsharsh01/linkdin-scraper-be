from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from bson import ObjectId
from bson.errors import InvalidId

from db.mongo import get_database
from services.apify_scrape import BYLINE_COLLECTION


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_byline_id(byline_id: str) -> ObjectId:
    try:
        return ObjectId(byline_id)
    except InvalidId as exc:
        msg = "Invalid byline id."
        raise ValueError(msg) from exc


def update_byline_status(user_id: UUID, byline_id: str, status: bool) -> dict[str, object]:
    database = get_database()
    col = database[BYLINE_COLLECTION]
    oid = _parse_byline_id(byline_id)
    user_id_str = str(user_id)

    result = col.update_one(
        {"_id": oid, "user_id": user_id_str},
        {"$set": {"status": status, "status_updated_at": _utcnow()}},
    )
    if result.matched_count == 0:
        msg = "Byline not found for this user."
        raise LookupError(msg)

    return {"id": str(oid), "user_id": user_id, "status": status}


def bulk_set_false_bylines_to_true(user_id: UUID) -> dict[str, int]:
    """Set status=True on every byline for this user where status is currently False."""
    database = get_database()
    col = database[BYLINE_COLLECTION]
    user_id_str = str(user_id)

    result = col.update_many(
        {"user_id": user_id_str, "status": False},
        {"$set": {"status": True, "status_updated_at": _utcnow()}},
    )
    return {
        "matched_count": result.matched_count,
        "modified_count": result.modified_count,
    }
