from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from apify_client import ApifyClient

from src.core.config import settings
from src.db.mongo import get_database
from src.schemas.apify_scrape import ApifyScrapeResponse, AuthorByline, SourceScrapeOutcome

logger = logging.getLogger(__name__)

APIFY_LINKEDIN_ACTOR_ID = "Wpp1BZ6yGWjySadk3"
RAW_COLLECTION = "linkedin_scrape_raw"
BYLINE_COLLECTION = "linkedin_author_bylines"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _utc_today_iso_date() -> str:
    """Date-only string (YYYY-MM-DD) for Apify scrapeUntil."""
    return _utcnow().date().isoformat()


def _item_to_byline(item: dict[str, Any]) -> AuthorByline:
    url_val = item.get("url")
    if url_val is not None and not isinstance(url_val, str):
        url_val = str(url_val)

    text_val = item.get("text")
    if text_val is not None and not isinstance(text_val, str):
        text_val = str(text_val)

    apu = item.get("authorProfileUrl")
    if apu is not None and not isinstance(apu, str):
        apu = str(apu)

    aname = item.get("authorName")
    if aname is not None and not isinstance(aname, str):
        aname = str(aname)

    return AuthorByline(
        text=text_val,
        url=url_val,
        authorProfileUrl=apu,
        authorName=aname,
    )


def _byline_document(user_id: str, source_url: str, byline: AuthorByline) -> dict[str, Any]:
    return {
        "user_id": user_id,
        "source_url": source_url,
        "created_at": _utcnow(),
        "text": byline.text,
        "url": byline.url,
        "authorProfileUrl": byline.authorProfileUrl,
        "authorName": byline.authorName,
        "status": False,
        "llm_response": None,
    }


def run_apify_scrape_for_user(
    user_id: UUID,
    max_sources: int | None,
    limit_per_source: int,
) -> ApifyScrapeResponse:
    if not settings.apify_client_key:
        msg = "APIFY_CLIENT_KEY is not configured."
        raise ValueError(msg)

    database = get_database()
    users_collection = database["users"]
    sources_collection = database["sources"]
    raw_collection = database[RAW_COLLECTION]
    byline_collection = database[BYLINE_COLLECTION]

    user_id_str = str(user_id)
    if users_collection.find_one({"user_id": user_id_str}) is None:
        msg = "User not found for the provided user_id."
        raise LookupError(msg)

    source_cursor = sources_collection.find({"user_id": user_id_str}).sort("id", 1)
    sources: list[dict[str, Any]] = list(source_cursor)
    if max_sources is not None:
        sources = sources[:max_sources]

    started_at = _utcnow()
    outcomes: list[SourceScrapeOutcome] = []
    author_bylines: list[AuthorByline] = []

    client = ApifyClient(settings.apify_client_key)
    scrape_until = _utc_today_iso_date()

    for source in sources:
        source_url = str(source.get("url", ""))
        outcome = SourceScrapeOutcome(source_url=source_url, raw_items_saved=0, author_bylines_saved=0)

        if not source_url:
            outcome.error = "Source document is missing a URL."
            outcomes.append(outcome)
            continue

        run_input: dict[str, Any] = {
            "urls": [source_url],
            "limitPerSource": limit_per_source,
            "scrapeUntil": scrape_until,
            "deepScrape": True,
            "rawData": False,
        }

        try:
            run = client.actor(APIFY_LINKEDIN_ACTOR_ID).call(run_input=run_input)
            dataset_id = run.get("defaultDatasetId")
            if not dataset_id:
                outcome.error = "Apify run completed without a defaultDatasetId."
                outcomes.append(outcome)
                continue

            for item in client.dataset(dataset_id).iterate_items():
                if not isinstance(item, dict):
                    continue

                raw_doc: dict[str, Any] = {
                    "user_id": user_id_str,
                    "source_url": source_url,
                    "created_at": _utcnow(),
                    "item": item,
                }
                raw_collection.insert_one(raw_doc)
                outcome.raw_items_saved += 1

                byline = _item_to_byline(item)
                byline_collection.insert_one(_byline_document(user_id_str, source_url, byline))
                outcome.author_bylines_saved += 1
                author_bylines.append(byline)

        except Exception as exc:  # noqa: BLE001 — surface per-source failures without aborting the batch
            logger.exception("Apify scrape failed for source_url=%s", source_url)
            outcome.error = str(exc)

        outcomes.append(outcome)

    finished_at = _utcnow()
    completed = sum(1 for o in outcomes if o.error is None)

    return ApifyScrapeResponse(
        user_id=user_id,
        sources_planned=len(outcomes),
        sources_completed=completed,
        outcomes=outcomes,
        author_bylines=author_bylines,
        started_at=started_at,
        finished_at=finished_at,
    )
