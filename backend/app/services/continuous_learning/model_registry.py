"""
model_registry.py — Phase 6
────────────────────────────
Versioned model store. Records every fine-tuned model with metadata
and accuracy metrics — allows safe rollback.

SQLite tables:
  model_registry  — one row per trained model version
  training_jobs   — one row per fine-tuning submission

Live model override:
  The active model ID is cached in _ACTIVE_OVERRIDE dict.
  llm_client.py checks this dict before using the default model.
"""
import os
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.logger import logger

_DB_PATH = os.path.join("data", "feedback.db")

# In-memory override for active model (read by llm_client)
_ACTIVE_OVERRIDE: Dict[str, Optional[str]] = {
    "groq":   None,
    "openai": None,
    "gemini": None,
}


def get_active_model(provider: str) -> Optional[str]:
    """Return the currently active fine-tuned model ID for a provider, or None."""
    return _ACTIVE_OVERRIDE.get(provider)


def set_active_model(provider: str, model_id: str) -> None:
    """Override the active model in memory (takes effect immediately)."""
    _ACTIVE_OVERRIDE[provider] = model_id
    logger.info(f"Model override set: provider={provider} model={model_id}")


_SCHEMA_REGISTRY = """
CREATE TABLE IF NOT EXISTS model_registry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version TEXT UNIQUE NOT NULL,
    provider TEXT NOT NULL,
    base_model TEXT,
    fine_tuned_model_id TEXT,
    dataset_path TEXT,
    dataset_entries INTEGER DEFAULT 0,
    training_job_id TEXT,
    accuracy_scam REAL DEFAULT 0.0,
    accuracy_safe REAL DEFAULT 0.0,
    fp_rate REAL DEFAULT 0.0,
    fn_rate REAL DEFAULT 0.0,
    is_active INTEGER DEFAULT 0,
    trained_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS training_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT,
    provider TEXT,
    status TEXT DEFAULT 'pending',
    submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    model_version TEXT,
    error TEXT
);
"""


async def init_registry() -> None:
    """Ensure registry tables exist."""
    try:
        import aiosqlite
        async with aiosqlite.connect(_DB_PATH) as db:
            await db.executescript(_SCHEMA_REGISTRY)
            await db.commit()
    except Exception as e:
        logger.error(f"Registry init failed: {e}")


async def register_model(
    version: str,
    provider: str,
    base_model: str,
    fine_tuned_model_id: str,
    dataset_path: str,
    dataset_entries: int,
    training_job_id: str = "",
    notes: str = ""
) -> bool:
    """Insert a new model version into the registry."""
    try:
        import aiosqlite
        async with aiosqlite.connect(_DB_PATH) as db:
            await db.execute(
                """INSERT OR REPLACE INTO model_registry
                   (version, provider, base_model, fine_tuned_model_id,
                    dataset_path, dataset_entries, training_job_id, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (version, provider, base_model, fine_tuned_model_id,
                 dataset_path, dataset_entries, training_job_id, notes)
            )
            await db.commit()
        logger.info(f"Model registered: version={version} provider={provider}")
        return True
    except Exception as e:
        logger.error(f"Registry insert failed: {e}")
        return False


async def activate_model(version: str) -> Dict[str, Any]:
    """
    Activate a specific model version.
    Deactivates all others first.
    Also sets in-memory override so llm_client uses it immediately.
    """
    try:
        import aiosqlite
        async with aiosqlite.connect(_DB_PATH) as db:
            # Fetch target model
            async with db.execute(
                "SELECT provider, fine_tuned_model_id FROM model_registry WHERE version = ?",
                (version,)
            ) as cursor:
                row = await cursor.fetchone()

            if not row:
                return {"success": False, "error": f"Version '{version}' not found"}

            provider, model_id = row[0], row[1]

            # Deactivate all, activate target
            await db.execute("UPDATE model_registry SET is_active = 0")
            await db.execute(
                "UPDATE model_registry SET is_active = 1 WHERE version = ?",
                (version,)
            )
            await db.commit()

        # Set in-memory override
        set_active_model(provider, model_id)

        logger.info(f"Model activated: version={version} ({provider}: {model_id})")
        return {
            "success": True,
            "version": version,
            "provider": provider,
            "model_id": model_id
        }

    except Exception as e:
        logger.error(f"Model activation failed: {e}")
        return {"success": False, "error": str(e)}


async def rollback_to(version: str) -> Dict[str, Any]:
    """Alias for activate_model — explicit rollback to a previous version."""
    logger.info(f"Rolling back to model version: {version}")
    return await activate_model(version)


async def list_versions() -> List[Dict[str, Any]]:
    """Return all registered model versions, newest first."""
    try:
        import aiosqlite
        async with aiosqlite.connect(_DB_PATH) as db:
            async with db.execute(
                """SELECT version, provider, base_model, fine_tuned_model_id,
                          dataset_entries, accuracy_scam, accuracy_safe,
                          fp_rate, fn_rate, is_active, trained_at, notes
                   FROM model_registry ORDER BY trained_at DESC"""
            ) as cursor:
                rows = await cursor.fetchall()

        return [
            {
                "version":          r[0],
                "provider":         r[1],
                "base_model":       r[2],
                "fine_tuned_model": r[3],
                "dataset_entries":  r[4],
                "accuracy_scam":    r[5],
                "accuracy_safe":    r[6],
                "fp_rate":          r[7],
                "fn_rate":          r[8],
                "is_active":        bool(r[9]),
                "trained_at":       r[10],
                "notes":            r[11]
            }
            for r in rows
        ]
    except Exception as e:
        logger.error(f"list_versions failed: {e}")
        return []


async def update_metrics(
    version: str,
    accuracy_scam: float,
    accuracy_safe: float,
    fp_rate: float,
    fn_rate: float
) -> None:
    """Update accuracy metrics after validation."""
    try:
        import aiosqlite
        async with aiosqlite.connect(_DB_PATH) as db:
            await db.execute(
                """UPDATE model_registry
                   SET accuracy_scam=?, accuracy_safe=?, fp_rate=?, fn_rate=?
                   WHERE version=?""",
                (accuracy_scam, accuracy_safe, fp_rate, fn_rate, version)
            )
            await db.commit()
    except Exception as e:
        logger.error(f"update_metrics failed: {e}")


async def record_training_job(
    job_id: str,
    provider: str,
    status: str,
    model_version: str,
    error: str = ""
) -> None:
    """Record a training job submission."""
    try:
        import aiosqlite
        async with aiosqlite.connect(_DB_PATH) as db:
            await db.execute(
                """INSERT INTO training_jobs (job_id, provider, status, model_version, error)
                   VALUES (?, ?, ?, ?, ?)""",
                (job_id, provider, status, model_version, error)
            )
            await db.commit()
    except Exception as e:
        logger.error(f"record_training_job failed: {e}")
