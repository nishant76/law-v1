"""
Celery worker task for daily eCourts hearing-date sync.
Thin wrapper only — all logic in services/ecourts_service.py.

Configure the beat schedule (e.g. daily 06:00 IST) separately in celery_app.
"""
from celery import shared_task
from celery.utils.log import get_task_logger
import asyncio

from sqlalchemy import select

from backend.models.law_user import User
from backend.services.ecourts_service import get_ecourts_service
from backend.core.database import AsyncSessionLocal

logger = get_task_logger(__name__)


@shared_task(
    name="ecourts.sync_hearings",
    bind=True,
    max_retries=3,
    default_retry_delay=600,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=3600,
)
def sync_ecourts_hearings(self):
    """Daily cron: sync hearing dates from eCourts for every lawyer who has set
    an advocate name. Scheduled: daily ~06:00 IST."""
    try:
        result = asyncio.run(_sync_all_async())
        logger.info(f"eCourts daily sync complete: {result} lawyers synced")
        return result
    except Exception as exc:
        logger.error(f"eCourts daily sync failed: {exc}")
        raise self.retry(exc=exc)


async def _sync_all_async() -> int:
    service = get_ecourts_service()
    if not service.configured:
        logger.warning("eCourts API not configured — skipping daily sync")
        return 0

    synced = 0
    async with AsyncSessionLocal() as session:
        stmt = select(User).where(
            User.ecourts_advocate_name.isnot(None),
            User.deleted_at.is_(None),
            User.is_active.is_(True),
        )
        users = (await session.execute(stmt)).scalars().all()
        for user in users:
            try:
                await service.sync_firm_hearings(
                    firm_id=str(user.firm_id),
                    advocate_name=user.ecourts_advocate_name,
                    session=session,
                )
                synced += 1
            except Exception as exc:
                logger.error(f"eCourts sync failed for user={user.id}: {exc}")
    return synced
