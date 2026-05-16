from __future__ import annotations

import logging
from uuid import UUID
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from src.core.config import settings
from src.services.scheduled_pipeline import run_scheduled_scrape_and_llm_for_user

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _scheduled_job() -> None:
    if not settings.scheduler_user_id:
        logger.warning("SCHEDULER_USER_ID is not set; scheduled scrape+LLM skipped.")
        return
    try:
        user_id = UUID(settings.scheduler_user_id)
    except ValueError:
        logger.error("SCHEDULER_USER_ID is not a valid UUID: %s", settings.scheduler_user_id)
        return
    run_scheduled_scrape_and_llm_for_user(user_id)


def start_scheduler() -> None:
    """Morning/evening runs from AM_Time_Harsh and PM_time_harsh in SCHEDULER_TIMEZONE."""
    global _scheduler

    if _scheduler is not None and _scheduler.running:
        return

    try:
        tz = ZoneInfo(settings.scheduler_timezone)
    except Exception:
        logger.exception("Invalid SCHEDULER_TIMEZONE=%s; falling back to UTC.", settings.scheduler_timezone)
        tz = ZoneInfo("UTC")

    am_h, am_m = settings.scheduler_am_hour, settings.scheduler_am_minute
    pm_h, pm_m = settings.scheduler_pm_hour, settings.scheduler_pm_minute

    _scheduler = BackgroundScheduler(timezone=tz)
    _scheduler.add_job(
        _scheduled_job,
        CronTrigger(hour=am_h, minute=am_m),
        id="linkedin_scrape_llm_morning",
        replace_existing=True,
    )
    _scheduler.add_job(
        _scheduled_job,
        CronTrigger(hour=pm_h, minute=pm_m),
        id="linkedin_scrape_llm_evening",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info(
        "APScheduler started AM=%02d:%02d PM=%02d:%02d timezone=%s user=%s",
        am_h,
        am_m,
        pm_h,
        pm_m,
        settings.scheduler_timezone,
        settings.scheduler_user_id or "(none)",
    )


def shutdown_scheduler() -> None:
    global _scheduler

    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("APScheduler shut down.")
    _scheduler = None
