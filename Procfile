web: python -c "
import os
import sys
from pathlib import Path

# Setup path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root / 'src'))

# Import and serve
from Guardian.app import app
from waitress import serve

port = int(os.environ['PORT'])
print(f'Starting on port {port}')
serve(app, host='0.0.0.0', port=port)
"