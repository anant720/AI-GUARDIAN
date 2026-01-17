#!/usr/bin/env python
"""
WSGI entry point for Railway deployment.
This provides a direct WSGI application that Railway can use.
"""

import os
import sys

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import the Flask app
from Guardian.app import app

# Railway expects the WSGI application to be named 'application'
application = app

if __name__ == "__main__":
    # For local testing
    port = int(os.environ.get('PORT', 5000))
    application.run(host='0.0.0.0', port=port, debug=False)