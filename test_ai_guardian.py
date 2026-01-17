# Test by importing the actual app
try:
    from src.Guardian.app import app
    print("Full app imported successfully")
except Exception as e:
    print(f"Full app import failed: {e}")
    import sys
    sys.exit(1)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)