"""
phase9/db_diagnostics.py
─────────────────────────
Handles fallback diagnostic capture if the PostgreSQL connection dies.
Writes vital configuration parameters safely to a local KanTool json file
so that developers can pinpoint whether env vars or passwords vanished.
"""
import os
import json
import platform
import hashlib
from datetime import datetime, timezone
from app.services.monitoring.error_logger import log_system_error
from app.logger import logger

def collect_env_and_dump():
    """
    Called by the monitoring loop if PostgreSQL is unreachable.
    Captures system state and dumps to KanTool folder.
    """
    logger.warning("Phase 9: Collecting diagnostics for DB Failure via KanTool.")
    
    # 1. Gather data
    env_info = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "DATABASE_URL": os.getenv("DATABASE_URL", "<NOT_SET>"),
        "REDIS_URL": os.getenv("REDIS_URL", "<NOT_SET>"),
        "JWT_SECRET_KEY": os.getenv("JWT_SECRET_KEY", "<NOT_SET>"),
        "JWT_SECRET_KEY_SHA256": hashlib.sha256(os.getenv("JWT_SECRET_KEY", "").encode("utf-8")).hexdigest()
        if os.getenv("JWT_SECRET_KEY")
        else None,
        "APP_VERSION": "v9.0",
        "OS": platform.platform(),
        "Python": platform.python_version()
    }
    
    # 2. Ensure KanTool directory exists
    kan_tool_path = os.getenv("KAN_TOOL_PATH", "C:/KanTool/ai_guardian_env.json")
    target_dir = os.path.dirname(kan_tool_path)
    try:
        os.makedirs(target_dir, exist_ok=True)
    except Exception as e:
        log_system_error("db_diagnostics", f"Failed to create KanTool directory {target_dir}: {e}")
        return False
        
    # 3. Write diagnostics
    try:
        with open(kan_tool_path, "w", encoding="utf-8") as f:
            json.dump(env_info, f, indent=4)
        logger.info(f"Phase 9 KanTool diagnostic written to {kan_tool_path}")
        return True
    except Exception as e:
        log_system_error("db_diagnostics", f"Failed to write to KanTool file {kan_tool_path}: {e}")
        return False
