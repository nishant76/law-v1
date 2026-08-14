"""
Celery worker tasks for the court diary.
Thin wrappers only — all logic in services/diary_service.py.

Scheduled in celery_app.beat_schedule:
  * send_daily_cause_list — 12:30 UTC = 18:00 IST, the evening before
  * materialise_diary_entries — 01:00 UTC = 06:30 IST, after the eCourts sync
"""
from celery import shared_task
from celery.utils.log import get_task_logger
import asyncio

from backend.core.database import AsyncSessionLocal
from backend.services.diary_service import get_diary_service

logger = get_task_logger(__name__)


@shared_task(
    name="diary.send_daily_cause_list",
    bind=True,
    max_retries=2,
    default_retry_delay=600,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=1800,
)
def send_daily_cause_list(self):
    """
    Evening cron: WhatsApp every opted-in lawyer their own cause list for
    tomorrow. Internal to the firm — not the client reminders.
    """
    try:
        sent = asyncio.run(_send_daily_cause_list_async())
        logger.info(f"Daily cause list sent to {sent} lawyers")
        return sent
    except Exception as exc:
        logger.error(f"Daily cause list failed: {exc}")
        raise self.retry(exc=exc)


async def _send_daily_cause_list_async() -> int:
    service = get_diary_service()
    async with AsyncSessionLocal() as session:
        return await service.send_daily_cause_lists(session)


@shared_task(
    name="diary.materialise_entries",
    bind=True,
    max_retries=2,
    default_retry_delay=600,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def materialise_diary_entries(self):
    """
    Morning cron: turn every matter's next_hearing_date (kept fresh by the
    eCourts sync) into a scheduled diary entry, so the day view and the cause
    list are complete without anyone opening the diary UI.
    """
    try:
        created = asyncio.run(_materialise_async())
        logger.info(f"Materialised {created} diary entries")
        return created
    except Exception as exc:
        logger.error(f"Diary materialisation failed: {exc}")
        raise self.retry(exc=exc)


async def _materialise_async() -> int:
    service = get_diary_service()
    async with AsyncSessionLocal() as session:
        return await service.ensure_scheduled_entries(session)
