"""
Celery application and task configuration
Daily cron jobs managed via Celery Beat
"""
from celery import Celery
from celery.schedules import crontab
from backend.core.config import settings

# Create Celery app
celery_app = Celery(
    "nikhar",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "backend.workers.document_ingest",
        "backend.workers.citations",
        "backend.workers.deadlines",
    ],
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes hard time limit
    result_expires=3600,  # 1 hour
)

# Task routing — all tasks use default queue in Phase 1
# (Phase 2: split into separate queues per worker type)

# Celery Beat schedule for periodic tasks
# Daily scraper_update: new government court judgments from eSCR + P&H HC
celery_app.conf.beat_schedule = {
    "scraper-update": {
        "task": "citations.scraper_update",
        "schedule": crontab(hour=2, minute=0),  # 02:00 UTC = 07:30 IST
        "options": {
            "queue": "scrapers",
            "priority": 8,  # High priority for data collection
        }
    },
}
