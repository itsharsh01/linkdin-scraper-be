from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from bson import ObjectId

from core.config import settings
from db.mongo import get_database
from services.apify_scrape import BYLINE_COLLECTION


def _day_range_utc(day: date, tz_name: str) -> tuple[datetime, datetime]:
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("UTC")
    start_local = datetime.combine(day, time.min, tzinfo=tz)
    end_local = datetime.combine(day, time.max, tzinfo=tz)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


def _serialize_byline(doc: dict[str, Any]) -> dict[str, Any]:
    oid = doc.get("_id")
    created = doc.get("created_at")
    if isinstance(created, datetime) and created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)

    llm = doc.get("llm_response")
    if llm is not None and not isinstance(llm, dict):
        llm = None

    return {
        "id": str(oid) if isinstance(oid, ObjectId) else str(oid or ""),
        "user_id": doc.get("user_id"),
        "source_url": doc.get("source_url"),
        "created_at": created,
        "text": doc.get("text"),
        "url": doc.get("url"),
        "author_profile_url": doc.get("authorProfileUrl"),
        "author_name": doc.get("authorName"),
        "status": doc.get("status"),
        "email_skip_reason": doc.get("email_skip_reason"),
        "llm_response": llm,
    }


def list_bylines_for_user_on_date(user_id: UUID, day: date) -> list[dict[str, Any]]:
    database = get_database()
    col = database[BYLINE_COLLECTION]
    user_id_str = str(user_id)
    start_utc, end_utc = _day_range_utc(day, settings.scheduler_timezone)

    cursor = col.find(
        {
            "user_id": user_id_str,
            "created_at": {"$gte": start_utc, "$lte": end_utc},
        }
    ).sort("created_at", -1)

    return [_serialize_byline(doc) for doc in cursor]
