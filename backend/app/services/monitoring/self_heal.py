"""
self_healing_engine.py
────────────────────
Attempts automatic recovery for vital services (Postgres, Redis, Background Loops).
This prevents the need for manual 'uvicorn' restarts when networking blips occur.
"""
import asyncio
from app.logger import logger
from app.services.monitoring.error_logger import log_system_error
from app.services.monitoring.alerting import send_dev_alert

# References to phase modules
from app.services.database.db import init_db, is_connected as pg_connected
from app.services.event_system import event_bus

async def attempt_pg_recovery() -> bool:
    """Attempts to cleanly re-initialise the asyncpg connection pool."""
    logger.info("Self-Healing Engine: Attempting PostgreSQL connection pool restart...")
    try:
        status = await init_db()
        if status.get("connected"):
            logger.info("Self-Healing Engine: PostgreSQL recovery SUCCESS.")
            return True
        else:
            logger.error("Self-Healing Engine: PostgreSQL recovery FAILED.")
            return False
    except Exception as e:
        log_system_error("self_heal", f"PostgreSQL self-heal crashed: {e}")
        return False

async def attempt_redis_recovery() -> bool:
    """Attempts to reconnect Redis."""
    logger.info("Self-Healing Engine: Attempting Redis Event Bus restart...")
    try:
        await event_bus.init_event_bus()
        if event_bus._redis_client:
            logger.info("Self-Healing Engine: Redis recovery SUCCESS.")
            return True
        else:
            logger.error("Self-Healing Engine: Redis recovery FAILED (using queue).")
            return False
    except Exception as e:
        log_system_error("self_heal", f"Redis self-heal crashed: {e}")
        return False

async def orchestrate_self_healing(component: str):
    """
    Dispatches targeted recovery attempts.
    If recovery fails, escalates to Developer Alerts.
    """
    success = False
    
    if component == "postgres":
        success = await attempt_pg_recovery()
    elif component == "redis":
        success = await attempt_redis_recovery()
    else:
        logger.warning(f"Self-Healing Engine: Unknown component '{component}'")
        return
        
    if not success:
        # Escalate
        await send_dev_alert(
            subject=f"CRITICAL: {component.upper()} Self-Healing Failed",
            message=f"The AI Guardian backend failed to automatically recover the {component} service. "
                    f"Check the server logs and the KanTool environment diagnostic immediately."
        )
