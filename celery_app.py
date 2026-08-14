"""
Celery application and task configuration
Daily cron jobs managed via Celery Beat
"""
from celery import Celery
from celery.schedules import crontab
from backend.core.config import settings

# Create Celery app
celery_app = Celery(
    "superadvocate",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "backend.workers.document_ingest",
        "backend.workers.citations",
        "backend.workers.deadlines",
        "backend.workers.diary",
        "backend.workers.ecourts",
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

# Celery Beat schedule for periodic tasks.
#
# All times are UTC (timezone="UTC" above). IST = UTC + 5:30.
# Order through the day matters: eCourts sync brings in fresh hearing dates,
# the diary then materialises them into entries, and only then do reminders go
# out — otherwise the morning reminder run works off yesterday's dates.
celery_app.conf.beat_schedule = {
    # 00:30 UTC = 06:00 IST — pull today's hearing dates from eCourts first.
    "ecourts-daily-sync": {
        "task": "ecourts.sync_hearings",
        "schedule": crontab(hour=0, minute=30),
        "options": {"queue": "celery", "priority": 7},
    },
    # 01:00 UTC = 06:30 IST — turn those dates into diary entries.
    "diary-materialise-entries": {
        "task": "diary.materialise_entries",
        "schedule": crontab(hour=1, minute=0),
        "options": {"queue": "celery", "priority": 6},
    },
    # 02:00 UTC = 07:30 IST — new government judgments.
    "scraper-update": {
        "task": "citations.scraper_update",
        "schedule": crontab(hour=2, minute=0),
        "options": {
            "queue": "scrapers",
            "priority": 8,  # High priority for data collection
        }
    },
    # 03:30 UTC = 09:00 IST — deadline reminders (in-app + email + client
    # WhatsApp), after the sync so 30/7/1 offsets reflect today's data.
    "deadline-reminders": {
        "task": "deadlines.process_reminders",
        "schedule": crontab(hour=3, minute=30),
        "options": {"queue": "celery", "priority": 9},
    },
    # 12:30 UTC = 18:00 IST — the lawyer's own cause list for TOMORROW.
    "daily-cause-list": {
        "task": "diary.send_daily_cause_list",
        "schedule": crontab(hour=12, minute=30),
        "options": {"queue": "celery", "priority": 7},
    },
}
