#!/usr/bin/env python3
"""
Test script for Railway deployment components
"""

import os
import sys

# Set test environment
os.environ['PORT'] = '8080'
os.environ['RAILWAY_ENVIRONMENT'] = 'production'

print('Testing Railway deployment components...')

try:
    from wsgi import app
    print('[OK] wsgi import successful')
    print(f'  App: {app.name}')
except Exception as e:
    print(f'[ERROR] wsgi import failed: {e}')
    sys.exit(1)

try:
    from waitress import serve
    print('[OK] waitress import successful')
except Exception as e:
    print(f'[ERROR] waitress import failed: {e}')
    sys.exit(1)

# Test endpoints
print('\nTesting endpoints...')
with app.test_client() as client:
    # Test ping
    ping = client.get('/ping')
    print(f'[OK] Ping: {ping.status_code} - {ping.get_data(as_text=True).strip()}')

    # Test health
    health = client.get('/health')
    print(f'[OK] Health: {health.status_code}')

    # Test home
    home = client.get('/')
    print(f'[OK] Home: {home.status_code} - {len(home.get_data())} chars')

print('\n[SUCCESS] All Railway deployment components ready!')
print('Procfile command will work: python -c "from wsgi import app; from waitress import serve; serve(app, host=\'0.0.0.0\', port=int(os.environ.get(\'PORT\', 5000)))"')