# src/Guardian/app.py

from flask import Flask, request, jsonify, render_template # Removed send_file
from flask_cors import CORS
import config
from .logger import setup_csv_logging

# Always import detection module - it handles lazy loading internally
from .detection import analyse_message
print("Detection module imported (models will load lazily)")

# The template folder is inside the Guardian package, so we specify the path relative to the package.
import os
template_path = os.path.join(os.path.dirname(__file__), 'templates')
app = Flask('Guardian', template_folder=template_path)

# Enable CORS to allow the demo interface (and other origins) to make API requests.
CORS(app, resources={
    r"/analyse": {"origins": config.API_CONFIG['CORS_ORIGINS']},
    r"/report": {"origins": config.API_CONFIG['CORS_ORIGINS']},
    r"/api/health": {"origins": ["*"]},
    r"/test": {"origins": ["*"]}
})

setup_csv_logging(app) # Integrate our custom CSV logger

@app.errorhandler(Exception)
def handle_exception(e):
    """Handle generic exceptions."""
    import traceback
    error_details = traceback.format_exc()
    app.logger.error(f"An unexpected error occurred: {e}")
    app.logger.error(f"Traceback: {error_details}")
    print(f"Flask error handler: {e}")
    print(f"Traceback: {error_details}")
    return jsonify(error="An internal server error occurred."), 500

@app.route("/health")
def health():
    """
    Health check endpoint to monitor system status.
    Shows whether models are loaded and system is ready.
    """
    return jsonify({
        "status": "ready",
        "version": "2.0"
    }), 200

@app.route("/test")
def test():
    """Simple test endpoint"""
    return "TEST OK", 200


@app.route("/analyse", methods=['POST'])
def analyse():
    """
    API endpoint to analyse a message.
    Always responds immediately - models load lazily if needed.
    Expects a JSON payload with a "message" key.
    e.g., {"message": "your message text here"}
    """
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({"error": "Invalid request. JSON with 'message' key required."}), 400

    message = data['message']
    result = analyse_message(message)

    # Log the analysis result using the app's logger.
    # The custom handler will pick this up and write it to the CSV.
    log_details = {
        "message": message,
        "level": result['level'],
        "score": result['score'],
        "reasons": '; '.join(result.get('reasons', []))
    }
    # The 'extra' dict makes the data available to our custom handler
    app.logger.info("Analysis performed", extra={'analysis_result': log_details})

    return jsonify(result)

@app.route("/demo")
def demo():
    """
    Serve the demo interface.
    """
    return home()

@app.route("/report", methods=['POST'])
def report():
    """
    API endpoint to report a false negative (message marked as safe but is dangerous).
    Expects a JSON payload with a "message" key.
    """
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({"error": "Invalid request. JSON with 'message' key required."}), 400

    message = data['message']
    # Log the report for manual review
    app.logger.info(f"User reported as dangerous: {message}")

    # Optionally, save to a file for later processing
    try:
        with open("reported_phishing.txt", "a", encoding="utf-8") as f:
            f.write(message + "\n")
    except Exception as e:
        app.logger.error(f"Error saving report: {e}")

    return jsonify({"status": "reported"}), 200

@app.route("/")
def home():
    """
    Serve the main demo interface.
    """
    # Flask's render_template will automatically look in the 'templates' folder
    return render_template("demo_interface.html")