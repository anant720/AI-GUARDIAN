"""
phase9/__init__.py
───────────────────
Public entry point: init_phase9() called from main.py lifespan.
"""
from app.services.monitoring.monitoring_health import start_monitoring_loop, stop_monitoring_loop
from app.services.monitoring.error_logger import log_system_error
from app.logger import logger

async def init_phase9():
    """Start the background monitoring process & reporting."""
    logger.info("Self-Healing & System Monitoring: Initialization Active")
    start_monitoring_loop()

async def shutdown_phase9():
    """Cleanly stop testing daemon."""
    await stop_monitoring_loop()

__all__ = ["init_phase9", "shutdown_phase9", "log_system_error"]
