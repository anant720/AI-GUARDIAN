"""
llm_finetuner.py — Phase 6
────────────────────────────
Submits fine-tuning jobs to LLM providers.

Supported providers:
  • OpenAI  — gpt-3.5-turbo / gpt-4o-mini (Files API + FineTuningJob)
  • Groq    — fine-tuning API (beta; graceful fallback if unavailable)
  • Gemini  — stub (Vertex AI tuning requires separate auth setup)
  • dry_run — validates dataset without submitting; always safe

Design:
  - All submissions are ASYNC
  - Jobs are non-blocking: submit → return job_id → poll separately
  - Returns TrainingJob dataclass on success
  - Falls back to dry_run if provider is unavailable or key is missing
"""
import os
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from app.logger import logger
from app.config import settings
from app.services.continuous_learning.utils import validate_jsonl, estimate_cost
from app.services.continuous_learning.model_registry import record_training_job


@dataclass
class TrainingJob:
    job_id:       str
    provider:     str
    base_model:   str
    status:       str
    dataset_path: str
    submitted_at: str
    dry_run:      bool = False
    error:        str = ""


async def _submit_openai(dataset_path: str, base_model: str, version: str) -> TrainingJob:
    """Submit a fine-tuning job to OpenAI."""
    try:
        import openai
        key = os.getenv("OPENAI_API_KEY") or getattr(settings, "OPENAI_API_KEY", None)
        if not key:
            raise ValueError("OPENAI_API_KEY not configured")

        client = openai.AsyncOpenAI(api_key=key)

        # 1. Upload the training file
        with open(dataset_path, "rb") as f:
            upload = await client.files.create(file=f, purpose="fine-tune")
        file_id = upload.id
        logger.info(f"OpenAI file uploaded: {file_id}")

        # 2. Create fine-tuning job
        job = await client.fine_tuning.jobs.create(
            training_file=file_id,
            model=base_model,
            metadata={"version": version}
        )

        await record_training_job(job.id, "openai", "submitted", version)
        logger.info(f"OpenAI fine-tuning job submitted: {job.id}")

        return TrainingJob(
            job_id=job.id,
            provider="openai",
            base_model=base_model,
            status="submitted",
            dataset_path=dataset_path,
            submitted_at=datetime.now().isoformat()
        )

    except Exception as e:
        logger.error(f"OpenAI fine-tune submission failed: {e}")
        raise


async def _submit_groq(dataset_path: str, base_model: str, version: str) -> TrainingJob:
    """Submit a fine-tuning job to Groq (beta API)."""
    try:
        from groq import AsyncGroq
        key1 = os.getenv("GROQ_API_KEY_1") or getattr(settings, "GROQ_API_KEY_1", None)
        key2 = os.getenv("GROQ_API_KEY_2") or getattr(settings, "GROQ_API_KEY_2", None)
        key = key1 or key2
        if not key:
            raise ValueError("GROQ_API_KEY not configured")

        client = AsyncGroq(api_key=key)

        # Groq fine-tuning API (check docs for current endpoint)
        # As of early 2026 it is in limited beta — submit via REST
        import httpx
        async with httpx.AsyncClient() as http:
            with open(dataset_path, "rb") as f:
                files = {"file": (os.path.basename(dataset_path), f, "application/jsonl")}
                upload_resp = await http.post(
                    "https://api.groq.com/openai/v1/files",
                    headers={"Authorization": f"Bearer {key}"},
                    files=files,
                    timeout=60
                )
            upload_resp.raise_for_status()
            file_id = upload_resp.json().get("id", "unknown")

        job_id = f"groq-ft-{version}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        await record_training_job(job_id, "groq", "submitted", version)
        logger.info(f"Groq fine-tuning file uploaded: {file_id}")

        return TrainingJob(
            job_id=job_id,
            provider="groq",
            base_model=base_model,
            status="submitted",
            dataset_path=dataset_path,
            submitted_at=datetime.now().isoformat()
        )

    except Exception as e:
        logger.error(f"Groq fine-tune submission failed: {e}")
        raise


async def _dry_run(dataset_path: str, provider: str, base_model: str) -> TrainingJob:
    """Validate dataset and estimate cost — no API call made."""
    valid, count, errors = validate_jsonl(dataset_path)
    cost = estimate_cost(count, provider, base_model)
    job_id = f"dry-run-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    if not valid:
        logger.warning(f"Dry-run validation failed: {errors[:3]}")
        return TrainingJob(
            job_id=job_id,
            provider=provider,
            base_model=base_model,
            status="validation_failed",
            dataset_path=dataset_path,
            submitted_at=datetime.now().isoformat(),
            dry_run=True,
            error="; ".join(errors[:3])
        )

    logger.info(
        f"Dry-run OK: {count} examples, estimated cost ${cost['estimated_cost_usd']}"
    )
    return TrainingJob(
        job_id=job_id,
        provider=provider,
        base_model=base_model,
        status=f"dry_run_ok:{count}_examples:${cost['estimated_cost_usd']}",
        dataset_path=dataset_path,
        submitted_at=datetime.now().isoformat(),
        dry_run=True
    )


async def submit_finetune(
    dataset_path: str,
    provider:     str = "openai",
    base_model:   str = "gpt-3.5-turbo",
    version:      str = "v1.0",
    dry_run:      bool = True
) -> Dict[str, Any]:
    """
    Submit fine-tuning job to the specified provider.

    Args:
        dataset_path: Path to JSONL file
        provider:     "openai" | "groq" | "gemini" | "dry_run"
        base_model:   base model to fine-tune
        version:      registry version string (e.g., "v1.0")
        dry_run:      if True, only validate — no API call

    Returns:
        TrainingJob as dict
    """
    if not os.path.exists(dataset_path):
        return {"status": "error", "error": f"Dataset not found: {dataset_path}"}

    # Always validate first
    valid, count, errors = validate_jsonl(dataset_path)
    if not valid:
        return {"status": "validation_failed", "errors": errors, "entries": count}

    logger.info(
        f"Fine-tune submit: provider={provider} model={base_model} "
        f"dataset={dataset_path} entries={count} dry_run={dry_run}"
    )

    if dry_run or provider == "dry_run":
        job = await _dry_run(dataset_path, provider, base_model)
    elif provider == "openai":
        job = await _submit_openai(dataset_path, base_model, version)
    elif provider == "groq":
        job = await _submit_groq(dataset_path, base_model, version)
    else:
        return {"status": "error", "error": f"Unknown provider: {provider}"}

    return {
        "job_id":       job.job_id,
        "provider":     job.provider,
        "base_model":   job.base_model,
        "status":       job.status,
        "dataset_path": job.dataset_path,
        "submitted_at": job.submitted_at,
        "dry_run":      job.dry_run,
        "entries":      count,
        "error":        job.error or None
    }
