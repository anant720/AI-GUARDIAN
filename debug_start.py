#!/usr/bin/env python3
"""
Debug script for start_demo.py
"""

import sys
import os
from pathlib import Path

def debug_imports():
    print("=== DEBUGGING IMPORTS ===")

    # Check Python path
    print(f"Python executable: {sys.executable}")
    print(f"Current working directory: {os.getcwd()}")

    # Check if src is in path
    project_root = Path(__file__).resolve().parent
    src_path = str(project_root / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
        print(f"Added to sys.path: {src_path}")

    # Test config import
    try:
        import config
        print("[OK] config import successful")
        print(f"  FLASK_HOST: {config.FLASK_HOST}")
        print(f"  FLASK_PORT: {config.FLASK_PORT}")
    except Exception as e:
        print(f"[ERROR] config import failed: {e}")
        return False

    # Test Guardian.app import
    try:
        from Guardian.app import app
        print("[OK] Guardian.app import successful")
        print(f"  App name: {app.name}")
    except Exception as e:
        print(f"[ERROR] Guardian.app import failed: {e}")
        return False

    return True

def debug_dependencies():
    print("\n=== DEBUGGING DEPENDENCIES ===")

    deps = ['flask', 'pandas', 'waitress', 'sklearn', 'joblib', 'requests', 'urlextract', 'flask_cors']

    for dep in deps:
        try:
            __import__(dep)
            print(f"[OK] {dep}")
        except ImportError as e:
            print(f"[MISSING] {dep}: {e}")
            return False

    return True

def debug_models():
    print("\n=== DEBUGGING MODEL FILES ===")

    import config

    model_path = Path('.') / config.MODEL_CONFIG['MODEL_PATH']
    vectorizer_path = Path('.') / config.MODEL_CONFIG['VECTORIZER_PATH']

    print(f"Model path: {model_path}")
    print(f"Model exists: {model_path.exists()}")

    print(f"Vectorizer path: {vectorizer_path}")
    print(f"Vectorizer exists: {vectorizer_path.exists()}")

    return model_path.exists() and vectorizer_path.exists()

def main():
    print("AI Guardian Debug Script")
    print("=" * 50)

    success = True

    success &= debug_imports()
    success &= debug_dependencies()
    success &= debug_models()

    if success:
        print("\n[SUCCESS] All checks passed! start_demo.py should work.")
    else:
        print("\n[FAILED] Some checks failed. Please fix the issues above.")

if __name__ == "__main__":
    main()