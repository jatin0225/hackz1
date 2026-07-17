"""APScheduler jobs: hourly ingestion + daily digest."""
import os
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from pipeline import run_full_pipeline
from email_service import send_daily_digest

log = logging.getLogger("scheduler")
_scheduler: AsyncIOScheduler = None


def start_scheduler(db):
    global _scheduler
    if _scheduler:
        return _scheduler
    _scheduler = AsyncIOScheduler(timezone="UTC")

    interval = int(os.environ.get("INGESTION_INTERVAL_MINUTES", "60"))
    _scheduler.add_job(lambda: run_full_pipeline(db, trigger="scheduler"),
                       IntervalTrigger(minutes=interval),
                       id="ingest",
                       replace_existing=True,
                       max_instances=1,
                       coalesce=True)

    # daily digest at 13:00 UTC (roughly morning US / evening EU)
    _scheduler.add_job(lambda: send_daily_digest(db),
                       CronTrigger(hour=13, minute=0),
                       id="digest",
                       replace_existing=True,
                       max_instances=1)

    _scheduler.start()
    log.info("Scheduler started: ingest every %s min, digest daily 13:00 UTC", interval)
    return _scheduler
