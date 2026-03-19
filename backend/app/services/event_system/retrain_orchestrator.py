"""
phase8/retrain_orchestrator.py
───────────────────────────────
Ties the Phase 6 Continuous Learning pipeline into the Phase 8 Event Bus.
Used by the /retrain/trigger API for on-demand scalable retraining.
"""
from app.logger import logger
from app.services.event_system.event_bus import publish_event
from app.services.continuous_learning import run_full_retrain_pipeline

async def trigger_manual_retrain(admin_user_id: int, dry_run: bool = True):
    """
    Executes the Phase 6 retrain pipeline.
    Emits bus events for success/failure, which in turn hit the alert manager & audit log.
    """
    logger.info(f"Phase 8: Manual retrain triggered by User {admin_user_id} (dry_run={dry_run})")
    
    # Emit start event
    await publish_event("retrain_started", {
        "user_id": admin_user_id,
        "dry_run": dry_run
    })

    try:
        # Run Phase 6 logic natively
        report = await run_full_retrain_pipeline(
            dry_run=dry_run, 
            auto_activate=False
        )
        
        # Emit complete event
        await publish_event("retrain_completed", {
            "user_id": admin_user_id,
            "status": report.status,
            "metrics": report.metrics,
            "model_id": getattr(report.model, "model_id", None) if report.model else None,
            "job_id": report.finetune_job_id,
            "dry_run": dry_run
        })
        
        return report

    except Exception as e:
        logger.error(f"Phase 8: Retrain Orchestrator failed: {e}")
        # Emit failure event
        await publish_event("retrain_failed", {
            "user_id": admin_user_id,
            "error": str(e)
        })
        raise
