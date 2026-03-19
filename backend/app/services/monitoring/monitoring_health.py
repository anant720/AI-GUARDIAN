"""
phase9/monitoring_health.py
────────────────────────────
The background pulse of Phase 9. Runs every N seconds.
Identifies failing subsystems and triggers 'self_heal' and 'db_diagnostics'.
"""
import os
import asyncio
from app.logger import logger

from app.services.database.db import is_connected as pg_connected
from app.services.event_system.event_bus import _redis_client
from app.services.monitoring.self_heal import orchestrate_self_healing
from app.services.monitoring.db_diagnostics import collect_env_and_dump
from app.services.monitoring.error_logger import log_system_error

_monitor_task: asyncio.Task = None
_MONITOR_INTERVAL = int(os.getenv("MONITOR_INTERVAL", "60"))

# State Tracking to prevent endless alerting
_pg_was_down = False
_redis_was_down = False

async def _health_loop():
    """Background asyncio task performing 60s health checks."""
    global _pg_was_down, _redis_was_down
    logger.info(f"Self-Healing & System Monitoring Health Loop started (interval={_MONITOR_INTERVAL}s)")

    while True:
        try:
            await asyncio.sleep(_MONITOR_INTERVAL)
            
            # --- 1. Check PostgreSQL ---
            if not pg_connected():
                if not _pg_was_down:
                    logger.error("Self-Healing & System Monitoring: PostgreSQL connection lost detected.")
                    # Drop KanTool Diagnostic
                    collect_env_and_dump()
                    # Trigger Self-Healing Attempt
                    asyncio.create_task(orchestrate_self_healing("postgres"))
                _pg_was_down = True
            else:
                if _pg_was_down:
                    logger.info("Self-Healing & System Monitoring: PostgreSQL connection recovered.")
                _pg_was_down = False

            # --- 2. Check Redis (if configured) ---
            if os.getenv("REDIS_URL"):
                try:
                    if _redis_client:
                        await _redis_client.ping()
                        if _redis_was_down:
                            logger.info("Self-Healing & System Monitoring: Redis connection recovered.")
                        _redis_was_down = False
                    else:
                        raise ConnectionError("Client is None")
                except Exception:
                    if not _redis_was_down:
                        logger.error("Self-Healing & System Monitoring: Redis connection lost detected.")
                        asyncio.create_task(orchestrate_self_healing("redis"))
                    _redis_was_down = True
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            log_system_error("monitoring_health", f"Unexpected failure in health loop: {e}")

def start_monitoring_loop():
    global _monitor_task
    if _monitor_task is None:
        _monitor_task = asyncio.create_task(_health_loop())

async def stop_monitoring_loop():
    global _monitor_task
    if _monitor_task:
        _monitor_task.cancel()
        try:
            await _monitor_task
        except asyncio.CancelledError:
            pass
        _monitor_task = None
