"""
Celery worker tasks for deadline processing
Thin wrappers only — all logic in services/
"""
from celery import shared_task
from celery.utils.log import get_task_logger
import asyncio

from backend.services.deadline_service import get_deadline_service
from backend.core.database import AsyncSessionLocal

logger = get_task_logger(__name__)


@shared_task(
    name="deadlines.process_reminders",
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 minutes
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=3600,  # Max 1 hour between retries
)
def process_deadline_reminders(self):
    """
    Daily cron task: Process due deadline reminders
    Sends notifications and WhatsApp messages

    Scheduled: Daily at 08:00 IST (02:30 UTC)
    """
    try:
        logger.info("Starting daily deadline reminder processing")

        # Run async code
        result = asyncio.run(_process_deadline_reminders_async())

        logger.info(f"Deadline reminder processing complete: {result} reminders processed")
        return result

    except Exception as exc:
        logger.error(f"Deadline reminder processing failed: {str(exc)}")

        # Retry with exponential backoff
        logger.warning(
            f"Retrying deadline processing {self.request.retries}/3"
        )
        raise self.retry(exc=exc)


async def _process_deadline_reminders_async() -> int:
    """
    Async implementation of deadline reminder processing
    All business logic delegated to DeadlineService
    """
    service = get_deadline_service()

    async with AsyncSessionLocal() as session:
        try:
            processed = await service.process_due_reminders(session)
            logger.info(f"Processed {processed} deadline reminders")
            return processed

        except Exception as exc:
            logger.error(f"Error in deadline reminder processing: {str(exc)}")
            raise