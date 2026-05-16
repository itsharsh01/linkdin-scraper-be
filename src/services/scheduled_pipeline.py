from __future__ import annotations

import logging
from uuid import UUID

from src.core.config import settings
from src.services.apify_scrape import run_apify_scrape_for_user
from src.services.byline_outreach_email import send_byline_outreach_emails
from src.services.linkedin_post_llm_pipeline import process_pending_bylines_with_llm

logger = logging.getLogger(__name__)


def run_scheduled_scrape_and_llm_for_user(user_id: UUID) -> None:
    """
    Scheduled pipeline: scrape all sources (LIMIT_PER_SOURCE_HARSH from .env), run LLM on new bylines,
    then send outreach emails for bylines that have an LLM payload and still status False; status
    becomes True only after an email is sent (or there is no valid recipient).
    """
    logger.info("Scheduled pipeline start user_id=%s", user_id)
    try:
        run_apify_scrape_for_user(
            user_id,
            max_sources=None,
            limit_per_source=settings.apify_limit_per_source,
        )
    except LookupError:
        logger.exception("Scheduled scrape aborted: user not found user_id=%s", user_id)
        return
    except ValueError:
        logger.exception("Scheduled scrape aborted: configuration error user_id=%s", user_id)
        return
    except Exception:
        logger.exception("Scheduled scrape failed user_id=%s", user_id)
        return

    try:
        stats = process_pending_bylines_with_llm(user_id)
        logger.info("Scheduled LLM batch finished user_id=%s stats=%s", user_id, stats)
    except Exception:
        logger.exception("Scheduled LLM batch failed user_id=%s", user_id)

    try:
        email_stats = send_byline_outreach_emails(user_id)
        logger.info("Scheduled outreach email batch finished user_id=%s stats=%s", user_id, email_stats)
    except Exception:
        logger.exception("Scheduled outreach email batch failed user_id=%s", user_id)
