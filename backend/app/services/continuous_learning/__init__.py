"""
phase6/__init__.py
──────────────────
Public entry point: run_full_retrain_pipeline()

Full Continuous Model Learning pipeline:
  1. process_feedback()      → List[LabeledExample]
  2. generate_dataset()      → JSONL file
  3. submit_finetune()       → TrainingJob
  4. register_model()        → model_registry entry
  5. activate_model()        → set as active (if auto_activate=True)

Returns a comprehensive ContinuousLearningReport dict.
"""
import os
from typing import Dict, Any, Optional
from datetime import datetime

from app.logger import logger
from app.services.continuous_learning.feedback_processor import process_feedback
from app.services.continuous_learning.dataset_generator import generate_dataset
from app.services.continuous_learning.llm_finetuner import submit_finetune
from app.services.continuous_learning.model_registry import (
    init_registry, register_model, activate_model, list_versions
)

# Config with sensible defaults
_PROVIDER    = os.getenv("FINETUNE_PROVIDER",     "openai")
_BASE_MODEL  = os.getenv("FINETUNE_BASE_MODEL",   "gpt-3.5-turbo")
_MAX_EXAMPLES= int(os.getenv("FINETUNE_MAX_EXAMPLES", "500"))
_DRY_RUN     = os.getenv("FINETUNE_DRY_RUN", "true").lower() != "false"


async def run_full_retrain_pipeline(
    dry_run:       Optional[bool] = None,
    auto_activate: bool = False,
    provider:      Optional[str] = None,
    base_model:    Optional[str] = None
) -> Dict[str, Any]:
    """
    Run the complete Continuous Model Learning pipeline.

    Args:
        dry_run:       Override FINETUNE_DRY_RUN env var (None = use env)
        auto_activate: Automatically activate new model if fine-tuning succeeds
        provider:      Override FINETUNE_PROVIDER env var
        base_model:    Override FINETUNE_BASE_MODEL env var

    Returns:
        ContinuousLearningReport dict with steps, dataset info, job info, and status.
    """
    dry_run    = dry_run    if dry_run    is not None else _DRY_RUN
    provider   = provider   or _PROVIDER
    base_model = base_model or _BASE_MODEL

    report: Dict[str, Any] = {
        "started_at": datetime.now().isoformat(),
        "dry_run":    dry_run,
        "provider":   provider,
        "base_model": base_model,
        "status":     "started"
    }

    # ── Step 1: Ensure registry tables exist ──────────────────────────────────
    await init_registry()

    # ── Step 2: Process feedback ──────────────────────────────────────────────
    logger.info("Continuous Model Learning — Step 1: Processing feedback...")
    examples = await process_feedback(min_confidence=0.4, limit=_MAX_EXAMPLES * 2)
    report["feedback_examples"] = len(examples)

    if not examples:
        report["status"] = "no_feedback"
        report["message"] = "No usable feedback records found — pipeline aborted"
        logger.info("Continuous Model Learning pipeline: no feedback to process")
        return report

    # ── Step 3: Generate dataset ──────────────────────────────────────────────
    logger.info(f"Continuous Model Learning — Step 2: Generating dataset from {len(examples)} examples...")
    dataset_info = await generate_dataset(examples, max_examples=_MAX_EXAMPLES)
    report["dataset"] = dataset_info

    if dataset_info.get("status") != "success" or not dataset_info.get("path"):
        report["status"] = "dataset_failed"
        return report

    dataset_path = dataset_info["path"]
    version      = dataset_info["version"]

    # ── Step 4: Submit fine-tuning ────────────────────────────────────────────
    logger.info(f"Continuous Model Learning — Step 3: Submitting fine-tune (dry_run={dry_run})...")
    job_info = await submit_finetune(
        dataset_path=dataset_path,
        provider=provider,
        base_model=base_model,
        version=version,
        dry_run=dry_run
    )
    report["training_job"] = job_info

    if job_info.get("status", "").startswith("error") or \
       job_info.get("status", "").startswith("validation_failed"):
        report["status"] = "finetune_failed"
        return report

    # ── Step 5: Register model in registry ───────────────────────────────────
    fine_tuned_id = job_info.get("job_id", "dry-run")
    if not dry_run:
        await register_model(
            version=version,
            provider=provider,
            base_model=base_model,
            fine_tuned_model_id=fine_tuned_id,
            dataset_path=dataset_path,
            dataset_entries=dataset_info.get("entries", 0),
            training_job_id=fine_tuned_id
        )
        report["model_registered"] = True

        # ── Step 6: Auto-activate if requested ───────────────────────────────
        if auto_activate:
            activation = await activate_model(version)
            report["model_activated"] = activation.get("success")
    else:
        report["model_registered"] = False
        report["note"] = "Dry-run mode: no model registered or activated"

    report["status"]       = "success"
    report["completed_at"] = datetime.now().isoformat()

    logger.info(
        f"Continuous Model Learning pipeline complete: "
        f"examples={len(examples)} entries={dataset_info.get('entries')} "
        f"job={fine_tuned_id} dry_run={dry_run}"
    )
    return report


__all__ = ["run_full_retrain_pipeline"]
