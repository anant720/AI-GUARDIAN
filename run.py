import os
import sys
from pathlib import Path

# Setup Python path
project_root = Path(__file__).resolve().parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Import app once
from Guardian.app import app
from waitress import serve

if __name__ == "__main__":
    serve(
        app,
        host="0.0.0.0",
        port=int(os.environ["PORT"])
    )