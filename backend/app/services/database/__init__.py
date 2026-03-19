"""
phase7/__init__.py
───────────────────
Public entry point: init_phase7() called from main.py lifespan.
"""
from app.services.database.db import init_db, close_db

async def init_phase7() -> dict:
    """Initialise PostgreSQL pool and create tables. Returns status dict."""
    return await init_db()

async def shutdown_phase7() -> None:
    """Close DB pool on shutdown."""
    await close_db()

__all__ = ["init_phase7", "shutdown_phase7"]
