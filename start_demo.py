#!/usr/bin/env python3
"""
AI Guardian Demo Startup Script
This script starts the Flask server and opens the demo interface.
"""

import subprocess
import webbrowser
import time
import os
import sys
import config # Moved import config to the top
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        import flask
        import pandas
        import waitress
        import sklearn
        import joblib
        import requests
        import urlextract
        import flask_cors
        print("All dependencies are installed.")
        return True
    except ImportError as e:
        missing_pkg = e.name
        print(f"Missing dependency: '{missing_pkg}'")
        print("Please install required packages by running:")
        print("pip install -r requirements.txt")
        return False

def start_server():
    """Start the Flask server."""
    print("Starting AI Guardian server...")

    # Start the Flask app
    try:
        # Add the 'src' directory to the path to resolve module imports
        # This ensures that the 'Guardian' package can be found.
        project_root = Path(__file__).resolve().parent
        sys.path.insert(0, str(project_root / "src"))

        from Guardian.app import app
        from waitress import serve # waitress import can stay here

        print(f"Server starting on http://{config.FLASK_HOST}:{config.FLASK_PORT}")
        print(f"Open the demo interface at: http://127.0.0.1:{config.FLASK_PORT}/")
        print(f"API endpoint is available at: http://127.0.0.1:{config.FLASK_PORT}/analyse")
        print("\nPress Ctrl+C to stop the server")

        # Open the demo page in the default web browser after a short delay
        demo_url = f"http://127.0.0.1:{config.FLASK_PORT}/"
        print(f"Opening demo interface at {demo_url} in your browser...")
        webbrowser.open_new_tab(demo_url)

        # Use a production-ready server instead of Flask's development server
        serve(app, host=config.FLASK_HOST, port=config.FLASK_PORT)

    except Exception as e:
        print(f"Error starting server: {e}")
        print("Common issues: Is another program using the same port? Are all dependencies installed?")
        sys.exit(1)

def main():
    """Main function to start the demo."""
    print("AI Guardian - Scam Detection Demo")
    print("=" * 50)

    # Check dependencies
    if not check_dependencies():
        sys.exit(1)

    # Verify that the essential model files exist before starting.
    model_path = Path(__file__).parent / config.MODEL_CONFIG['MODEL_PATH']
    if not model_path.exists():
        print(f"Error: Model file not found at '{model_path}'")
        print("Please ensure the model.joblib and vectorizer.joblib files are in src/Guardian/model/.")
        sys.exit(1)

    # Start the server
    print("\n" + "=" * 50)
    start_server()

if __name__ == "__main__":
    main()