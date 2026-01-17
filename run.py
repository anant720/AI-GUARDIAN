#!/usr/bin/env python3
"""
Railway production runner for AI Guardian.
Dedicated script to ensure Railway compatibility.
"""

import os
import sys
import logging
import time
from pathlib import Path

# Set up immediate logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True  # Override any existing handlers
)
logger = logging.getLogger(__name__)

def main():
    """Main entry point for Railway deployment."""
    start_time = time.time()
    logger.info("=== AI GUARDIAN RAILWAY STARTUP ===")
    logger.info(f"Process started at {time.ctime(start_time)}")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"Process ID: {os.getpid()}")

    # Critical: Get PORT from environment
    port_str = os.environ.get("PORT")
    if not port_str:
        logger.error("CRITICAL: PORT environment variable not set!")
        sys.exit(1)

    try:
        port = int(port_str)
        logger.info(f"PORT environment variable: {port}")
    except ValueError:
        logger.error(f"CRITICAL: Invalid PORT value: {port_str}")
        sys.exit(1)

    # Set up Python path
    project_root = Path(__file__).resolve().parent
    src_path = project_root / "src"
    sys.path.insert(0, str(src_path))
    logger.info(f"Added to sys.path: {src_path}")

    # Import Flask app - this must succeed
    logger.info("Importing Flask application...")
    try:
        from wsgi import app
        logger.info("Flask app imported successfully")
        logger.info(f"App name: {app.name}")
    except Exception as e:
        logger.error(f"CRITICAL: Failed to import Flask app: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

    # Test critical endpoints before starting server
    logger.info("Testing critical endpoints...")
    try:
        with app.test_client() as client:
            # Test railway endpoint
            railway_resp = client.get('/railway')
            logger.info(f"/railway endpoint: {railway_resp.status_code}")

            # Test ping endpoint
            ping_resp = client.get('/ping')
            logger.info(f"/ping endpoint: {ping_resp.status_code}")

            # Test health endpoint
            health_resp = client.get('/health')
            logger.info(f"/health endpoint: {health_resp.status_code}")

            # Test root endpoint
            root_resp = client.get('/')
            logger.info(f"/ endpoint: {root_resp.status_code}")

    except Exception as e:
        logger.error(f"CRITICAL: Endpoint testing failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

    # Import waitress - must be available
    logger.info("Importing Waitress server...")
    try:
        from waitress import serve
        logger.info("Waitress imported successfully")
    except ImportError as e:
        logger.error(f"CRITICAL: Waitress not available: {e}")
        sys.exit(1)

    # Final setup verification
    setup_time = time.time() - start_time
    logger.info(".2f")
    logger.info("=== STARTING PRODUCTION SERVER ===")

    # Start server with explicit settings
    try:
        logger.info(f"Binding to host=0.0.0.0, port={port}")
        logger.info("Starting Waitress server...")

        # Railway-compatible settings - no threads, no async
        serve(
            app,
            host="0.0.0.0",
            port=port,
            threads=1,  # Single thread for Railway Free tier
            connection_limit=100,
            channel_timeout=30,
            cleanup_interval=30,
            log_socket_errors=True
        )

    except Exception as e:
        logger.error(f"CRITICAL: Server failed to start: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()