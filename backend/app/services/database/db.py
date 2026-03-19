"""
db.py - Persistent Analytics Suite (PostgreSQL)
─────────────────────────────────────────────────────────────
Uses asyncpg for fully async DB access.

Graceful degradation: if DATABASE_URL is not configured or the DB is
unreachable, _POOL remains None and all callers receive a clear 503.
"""
import os
from contextlib import asynccontextmanager
from typing import Optional, AsyncGenerator
import asyncpg
from asyncpg import Pool, Connection

from app.logger import logger

_POOL: Optional[Pool] = None

# ── DDL — Persistent Analytics Suite — all tables ──────────────────────────────
_DDL = """
CREATE TABLE IF NOT EXISTS users (
    user_id     SERIAL PRIMARY KEY,
    username    VARCHAR(50)  UNIQUE NOT NULL,
    email       VARCHAR(100) UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    role        VARCHAR(20)  NOT NULL DEFAULT 'user',
    created_at  TIMESTAMPTZ  DEFAULT NOW(),
    last_login  TIMESTAMPTZ
);

-- Backfill legacy role values if present
UPDATE users SET role='user' WHERE role='standard';
ALTER TABLE users ALTER COLUMN role SET DEFAULT 'user';

CREATE TABLE IF NOT EXISTS user_permissions (
    permission_id      SERIAL PRIMARY KEY,
    user_id            INT REFERENCES users(user_id) ON DELETE CASCADE,
    can_retrain        BOOLEAN DEFAULT FALSE,
    can_view_dashboard BOOLEAN DEFAULT TRUE,
    can_manage_users   BOOLEAN DEFAULT FALSE,
    UNIQUE(user_id)
);

CREATE TABLE IF NOT EXISTS user_notifications (
    notification_id  SERIAL PRIMARY KEY,
    user_id          INT REFERENCES users(user_id) ON DELETE SET NULL,
    app_name         VARCHAR(100),
    message_text     TEXT,
    url              TEXT,
    risk_score       INT  DEFAULT 0,
    scam_probability INT  DEFAULT 0,
    phase5_behavior  JSONB,
    llm_verdict      JSONB,
    phase_outputs    JSONB,
    processed        BOOLEAN DEFAULT FALSE,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE user_notifications
    ADD COLUMN IF NOT EXISTS phase_outputs JSONB;

CREATE TABLE IF NOT EXISTS notification_interactions (
    interaction_id    SERIAL PRIMARY KEY,
    notification_id   INT REFERENCES user_notifications(notification_id) ON DELETE CASCADE,
    action_type       VARCHAR(50) NOT NULL,
    action_timestamp  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_notification_stats (
    stat_id              SERIAL PRIMARY KEY,
    user_id              INT REFERENCES users(user_id) ON DELETE CASCADE UNIQUE,
    total_notifications  INT   DEFAULT 0,
    scam_notifications   INT   DEFAULT 0,
    avg_risk_score       FLOAT DEFAULT 0.0,
    last_updated         TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS app_notification_stats (
    stat_id                  SERIAL PRIMARY KEY,
    app_name                 VARCHAR(100) UNIQUE NOT NULL,
    total_notifications      INT   DEFAULT 0,
    high_risk_notifications  INT   DEFAULT 0,
    last_updated             TIMESTAMPTZ DEFAULT NOW()
);

-- ── Real-time Event Orchestrator Tables ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS system_alerts (
    alert_id         SERIAL PRIMARY KEY,
    user_id          INT REFERENCES users(user_id) ON DELETE CASCADE,
    notification_id  INT REFERENCES user_notifications(notification_id) ON DELETE CASCADE,
    alert_type       VARCHAR(50),
    severity         INT,
    message          TEXT,
    triggered_at     TIMESTAMPTZ DEFAULT NOW(),
    acknowledged     BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS event_log (
    event_id         SERIAL PRIMARY KEY,
    event_type       VARCHAR(50) NOT NULL,
    user_id          INT,
    notification_id  INT,
    payload          JSONB,
    timestamp        TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS system_metrics (
    metric_id        SERIAL PRIMARY KEY,
    metric_name      VARCHAR(50) NOT NULL,
    value            FLOAT NOT NULL,
    recorded_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Indexes ──────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_notifications_user
    ON user_notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_created
    ON user_notifications(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_interactions_notification
    ON notification_interactions(notification_id);

CREATE INDEX IF NOT EXISTS idx_sys_metrics_time
    ON system_metrics(recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_sys_alerts_unack
    ON system_alerts(acknowledged) WHERE acknowledged = FALSE;
"""



async def init_db() -> dict:
    """
    Create the connection pool and run DDL to bootstrap tables.

    Returns a status dict — never raises, so startup never crashes.
    """
    global _POOL
    url = os.getenv("DATABASE_URL", "")
    if not url:
        logger.warning("Persistent Analytics Suite: DATABASE_URL not set — PostgreSQL logging disabled")
        return {"connected": False, "reason": "DATABASE_URL not configured"}

    try:
        _POOL = await asyncpg.create_pool(
            url,
            min_size=2,
            max_size=10,
            command_timeout=30,
            server_settings={"application_name": "ai_guardian"}
        )
        async with _POOL.acquire() as conn:
            await conn.execute(_DDL)
        logger.info("Persistent Analytics Suite: PostgreSQL connected and schema ready")
        return {"connected": True}
    except Exception as e:
        _POOL = None
        logger.error(f"Persistent Analytics Suite: PostgreSQL connection failed — {e}")
        return {"connected": False, "reason": str(e)}


async def close_db() -> None:
    """Close the pool on shutdown."""
    global _POOL
    if _POOL:
        await _POOL.close()
        _POOL = None
        logger.info("Persistent Analytics Suite: PostgreSQL pool closed")


def is_connected() -> bool:
    return _POOL is not None


@asynccontextmanager
async def get_conn() -> AsyncGenerator[Connection, None]:
    """
    Async context manager yielding a pooled connection.

    Usage:
        async with get_conn() as conn:
            await conn.fetch(...)

    Raises RuntimeError if pool is not initialised.
    """
    if _POOL is None:
        raise RuntimeError("PostgreSQL pool not initialised — check DATABASE_URL")
    async with _POOL.acquire() as conn:
        yield conn
