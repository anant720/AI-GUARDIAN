"""
retrain_scheduler.py — Continuous Model Learning
────────────────────────────────
Uses APScheduler (AsyncIOScheduler) to automate periodic retraining.

Schedule:
  - Reads RETRAIN_SCHEDULE_CRON from .env (default: weekly Sunday 2am)
  - Only triggers if >= RETRAIN_MIN_FEEDBACK new FP/FN records exist
  - Runs full pipeline non-blocking (asyncio background task)
  - Stores job results in training_jobs table

Usage:
  Called from app/main.py lifespan events:
    scheduler = FineTuneScheduler()
    await scheduler.start()   # on startup
    await scheduler.stop()    # on shutdown
"""
import asyncio
import os
from typing import Optional
from datetime import datetime

from app.logger import logger
from app.config import settings

# Minimum feedback records before auto-retrain triggers
_MIN_FEEDBACK = int(os.getenv("RETRAIN_MIN_FEEDBACK", "20"))
_CRON = os.getenv("RETRAIN_SCHEDULE_CRON", "0 2 * * 0")  # weekly Sunday 2am
_ENABLED = os.getenv("RETRAIN_SCHEDULER_ENABLED", "false").lower() == "true"


async def _get_feedback_count() -> int:
    """Count unprocessed FP + FN records."""
    try:
        import aiosqlite
        db_path = os.path.join("data", "feedback.db")
        if not os.path.exists(db_path):
            return 0
        async with aiosqlite.connect(db_path) as db:
            async with db.execute(
                """SELECT COUNT(*) FROM scan_feedback
                   WHERE system_verdict != user_correction"""
            ) as cursor:
                row = await cursor.fetchone()
        return row[0] if row else 0
    except Exception:
        return 0


async def _run_pipeline_safe() -> None:
    """
    Background retrain pipeline with full error isolation.
    Imports lazily to avoid circular imports.
    """
    try:
        from app.services.continuous_learning import run_full_retrain_pipeline
        logger.info("Scheduled retrain: starting pipeline")
        result = await run_full_retrain_pipeline(dry_run=False, auto_activate=True)
        logger.info(f"Scheduled retrain complete: {result.get('status')} | "
                    f"entries={result.get('dataset', {}).get('entries', 0)}")
    except Exception as e:
        logger.error(f"Scheduled retrain failed: {e}")


async def _cron_tick() -> None:
    """Run when the cron fires — checks threshold before triggering."""
    count = await _get_feedback_count()
    logger.info(f"Retrain scheduler tick: {count} FP/FN records (min={_MIN_FEEDBACK})")

    if count < _MIN_FEEDBACK:
        logger.info(f"Retrain skipped — insufficient feedback ({count} < {_MIN_FEEDBACK})")
        return

    # Run in background so scheduler tick is non-blocking
    asyncio.create_task(_run_pipeline_safe())


class FineTuneScheduler:
    """Wrapper around APScheduler AsyncIOScheduler."""

    def __init__(self):
        self._scheduler = None
        self._enabled   = _ENABLED

    def _parse_cron(self, cron_str: str) -> dict:
        """Parse '0 2 * * 0' format → APScheduler CronTrigger kwargs."""
        parts = cron_str.strip().split()
        if len(parts) != 5:
            logger.warning(f"Invalid RETRAIN_SCHEDULE_CRON '{cron_str}' — using default")
            parts = ["0", "2", "*", "*", "0"]
        keys = ["minute", "hour", "day", "month", "day_of_week"]
        return {k: v for k, v in zip(keys, parts) if v != "*"}

    async def start(self) -> None:
        """Start the scheduler on application startup."""
        if not self._enabled:
            logger.info("Retrain scheduler disabled (RETRAIN_SCHEDULER_ENABLED=false)")
            return

        try:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            from apscheduler.triggers.cron import CronTrigger

            self._scheduler = AsyncIOScheduler()
            cron_kwargs = self._parse_cron(_CRON)

            self._scheduler.add_job(
                _cron_tick,
                trigger=CronTrigger(**cron_kwargs),
                id="learning_retrain",
                replace_existing=True,
                max_instances=1
            )
            self._scheduler.start()
            logger.info(f"Continuous Model Learning: Scheduler started — cron: '{_CRON}'")

        except ImportError:
            logger.warning(
                "APScheduler not installed — retrain scheduler disabled. "
                "Install with: pip install apscheduler"
            )
        except Exception as e:
            logger.error(f"Retrain scheduler start failed: {e}")

    async def stop(self) -> None:
        """Shut down the scheduler on application shutdown."""
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("Retrain scheduler stopped")

    def get_status(self) -> dict:
        """Return scheduler status for /admin/feedback/stats."""
        if not self._scheduler:
            return {"running": False, "enabled": self._enabled, "cron": _CRON}
        jobs = self._scheduler.get_jobs()
        next_run = jobs[0].next_run_time.isoformat() if jobs else None
        return {
            "running":   self._scheduler.running,
            "enabled":   self._enabled,
            "cron":      _CRON,
            "next_run":  next_run,
            "min_feedback_threshold": _MIN_FEEDBACK
        }


# Global singleton — imported by main.py
scheduler = FineTuneScheduler()
