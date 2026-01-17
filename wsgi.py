#!/usr/bin/env python3
"""
WSGI entry point for Railway deployment.
This file provides a standard WSGI application object that Railway can import and serve.
"""

import os
import sys
import logging
from pathlib import Path

# Set up logging immediately
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

logger.info("Starting WSGI entry point for Railway deployment")

# Log environment info
logger.info(f"Python version: {sys.version}")
logger.info(f"Current working directory: {os.getcwd()}")
logger.info(f"Environment variables: PORT={os.environ.get('PORT', 'not set')}, RAILWAY_ENVIRONMENT={os.environ.get('RAILWAY_ENVIRONMENT', 'not set')}")

# Add the 'src' directory to the path to resolve module imports
try:
    project_root = Path(__file__).resolve().parent
    logger.info(f"Project root from __file__: {project_root}")
except NameError:
    project_root = Path.cwd()
    logger.info(f"Project root fallback: {project_root}")

src_path = project_root / "src"
sys.path.insert(0, str(src_path))
logger.info(f"Added to sys.path: {src_path}")
logger.info(f"sys.path now includes: {[p for p in sys.path if 'src' in p or 'Guardian' in p]}")

# Set Railway environment
os.environ.setdefault('RAILWAY_ENVIRONMENT', 'production')
logger.info(f"Railway environment set to: {os.environ.get('RAILWAY_ENVIRONMENT')}")

# Import the Flask app - this will trigger all initialization
logger.info("Importing Guardian.app...")
try:
    from Guardian.app import app
    logger.info("Guardian.app imported successfully")
    logger.info(f"Flask app name: {app.name}")
    logger.info(f"Flask app has {len(app.url_map._rules)} routes")
except Exception as e:
    logger.error(f"Failed to import Guardian.app: {e}")
    import traceback
    logger.error(traceback.format_exc())
    raise

# Railway will automatically detect and serve this 'app' object
logger.info("[OK] WSGI module loaded successfully")
logger.info(f"Application: {app.name}")
logger.info(f"Environment: {os.environ.get('RAILWAY_ENVIRONMENT', 'unknown')}")
logger.info(f"Port: {os.environ.get('PORT', 'unknown')}")

# Test that we can access basic endpoints without starting the server
logger.info("Testing basic endpoints...")
try:
    with app.test_client() as client:
        # Test ping
        ping_response = client.get('/ping')
        logger.info(f"Ping endpoint: {ping_response.status_code} - {ping_response.get_data(as_text=True)}")

        # Test health
        health_response = client.get('/health')
        logger.info(f"Health endpoint: {health_response.status_code}")

        # Test home page
        home_response = client.get('/')
        logger.info(f"Home endpoint: {home_response.status_code} - Content length: {len(home_response.get_data())}")

except Exception as e:
    logger.error(f"Endpoint testing failed: {e}")
    import traceback
    logger.error(traceback.format_exc())

logger.info("WSGI initialization complete - ready for Railway")

# For debugging - Railway logs will show this
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting development server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)