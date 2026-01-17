#!/usr/bin/env python3
"""
WSGI entry point for Railway deployment.
This file provides a standard WSGI application object that Railway can import and serve.
"""

import os
import sys
from pathlib import Path

# Add the 'src' directory to the path to resolve module imports
try:
    project_root = Path(__file__).resolve().parent
except NameError:
    # Fallback if __file__ is not available
    project_root = Path.cwd()
sys.path.insert(0, str(project_root / "src"))

# Set Railway environment
os.environ.setdefault('RAILWAY_ENVIRONMENT', 'production')

from Guardian.app import app

# Railway will automatically detect and serve this 'app' object
print("[OK] WSGI module loaded successfully")
print(f"Application: {app.name}")
print(f"Environment: {os.environ.get('RAILWAY_ENVIRONMENT', 'unknown')}")
print(f"Port: {os.environ.get('PORT', 'unknown')}")

# For debugging - Railway logs will show this
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)