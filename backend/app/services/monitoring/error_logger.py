"""
phase9/error_logger.py
───────────────────────
Centralized error logging for Phase 9 Testing & Monitoring.
Maintains a rotating file handler to prevent log bloat, specifically
tailored to capture stack traces and API endpoint failures.
"""
import logging
from logging.handlers import RotatingFileHandler
import os

LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "logs")
os.makedirs(LOG_DIR, exist_ok=True)
ERROR_LOG_FILE = os.path.join(LOG_DIR, "error.log")

# Setup generic error logger
error_logger = logging.getLogger("ai_guardian_errors")
error_logger.setLevel(logging.ERROR)

if not error_logger.handlers:
    # 5 MB per file, keep 3 backups
    handler = RotatingFileHandler(ERROR_LOG_FILE, maxBytes=5*1024*1024, backupCount=3)
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] [Module:%(module)s] - %(message)s'
    )
    handler.setFormatter(formatter)
    error_logger.addHandler(handler)

def log_system_error(module_name: str, error_message: str, exc_info: bool = True):
    """
    Log a system-level failure (used by self-healing and testing).
    """
    # Temporarily override the %(module)s format context
    extra = {"module": module_name}
    error_logger.error(error_message, exc_info=exc_info, extra=extra)

