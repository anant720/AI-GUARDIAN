# src/Guardian/app.py

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import config
import os
from .logger import setup_csv_logging
from .detection import analyse_message

# Simple Flask app setup
template_path = os.path.join(os.path.dirname(__file__), 'templates')
app = Flask('Guardian', template_folder=template_path)

# Enable CORS
CORS(app, resources={
    r"/analyse": {"origins": config.API_CONFIG['CORS_ORIGINS']},
    r"/report": {"origins": config.API_CONFIG['CORS_ORIGINS']},
    r"/health": {"origins": ["*"]}
})

setup_csv_logging(app)

@app.errorhandler(Exception)
def handle_exception(e):
    """Handle generic exceptions."""
    app.logger.error(f"An unexpected error occurred: {e}")
    return jsonify(error="An internal server error occurred."), 500

@app.route("/ping")
def ping():
    """
    Simple ping endpoint that responds immediately.
    Used for health checks and to verify the app is responding.
    """
    return "pong", 200

@app.route("/railway")
def railway():
    """
    Dedicated Railway health check endpoint.
    Returns plain text "OK" in under 10ms.
    No imports, no processing - just confirms service is alive.
    """
    return "OK", 200

@app.route("/health")
def health():
    """
    Health check endpoint that ALWAYS returns 200 in production.
    Railway uses this for service health checks - always return OK when service is running.
    """
    try:
        from .detection import _ml_model_loaded, _model_load_error

        status = {
            "status": "ready" if _ml_model_loaded else "initializing",
            "models_loaded": _ml_model_loaded,
            "timestamp": os.environ.get('SOURCE_VERSION', 'unknown'),
            "version": "2.0",
            "environment": os.environ.get('RAILWAY_ENVIRONMENT', 'unknown'),
            "port": os.environ.get('PORT', 'unknown')
        }

        if _model_load_error:
            status["model_error"] = str(_model_load_error)

        # ALWAYS return 200 for Railway health checks - service is running
        return jsonify(status), 200

    except Exception as e:
        app.logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "version": "2.0"
        }), 200  # Still return 200 even on error - service is responding


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
    return render_template("demo_interface.html")