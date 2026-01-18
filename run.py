import os
import sys
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Setup Python path
project_root = Path(__file__).resolve().parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))
logger.info(f"Python path set to: {src_path}")

# Check PORT environment variable
port_str = os.environ.get("PORT")
if not port_str:
    logger.error("CRITICAL: PORT environment variable not found!")
    sys.exit(1)

try:
    port = int(port_str)
    logger.info(f"Starting server on port {port}")
except ValueError:
    logger.error(f"CRITICAL: Invalid PORT value: {port_str}")
    sys.exit(1)

# Import app once
logger.info("Importing Flask app...")
try:
    from Guardian.app import app
    logger.info(f"Flask app imported: {app.name}")
except Exception as e:
    logger.error(f"CRITICAL: Failed to import app: {e}")
    sys.exit(1)

# Import waitress
try:
    from waitress import serve
    logger.info("Waitress imported successfully")
except ImportError as e:
    logger.error(f"CRITICAL: Waitress not available: {e}")
    sys.exit(1)

if __name__ == "__main__":
    logger.info(f"Starting Waitress server on 0.0.0.0:{port}")
    try:
        serve(
            app,
            host="0.0.0.0",
            port=port,
            threads=1,
            connection_limit=50
        )
    except Exception as e:
        logger.error(f"CRITICAL: Server failed to start: {e}")
        sys.exit(1)