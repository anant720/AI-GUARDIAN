"""
phase8/__init__.py
───────────────────
Public entry point: init_phase8() called from main.py lifespan.
"""
from app.services.event_system.event_bus import init_event_bus, close_event_bus, start_consumer, stop_consumer
from app.services.event_system.alert_manager import setup_alert_manager
from app.services.event_system.analytics_pipeline import start_analytics_pipeline, stop_analytics_pipeline

async def init_phase8():
    """Initialise Event Bus (Redis/Memory), Subscriptions, and Analytics Pipeline."""
    await init_event_bus()
    await setup_alert_manager()
    start_consumer()
    start_analytics_pipeline()

async def shutdown_event_orchestrator():
    """Shutdown event orchestration resources gracefully."""
    await stop_analytics_pipeline()
    await stop_consumer()
    await close_event_bus()

__all__ = ["init_phase8", "shutdown_phase8"]
