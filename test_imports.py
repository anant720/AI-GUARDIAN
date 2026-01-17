#!/usr/bin/env python3
"""
Test script to check if all dependencies can be imported
"""

def test_imports():
    """Test if required dependencies are installed."""
    required_modules = [
        ('flask', 'Flask web framework'),
        ('pandas', 'Data processing'),
        ('waitress', 'WSGI server'),
        ('sklearn', 'Machine learning'),
        ('joblib', 'Model serialization'),
        ('requests', 'HTTP requests'),
        ('urlextract', 'URL extraction'),
        ('flask_cors', 'CORS handling')
    ]

    missing_deps = []

    print("Testing dependency imports...")
    print("=" * 50)

    for module_name, description in required_modules:
        try:
            __import__(module_name)
            print(f"[OK] {module_name} - {description}")
        except ImportError as e:
            missing_deps.append(module_name)
            print(f"[MISSING] {module_name} - {description} - Error: {e}")

    print("=" * 50)
    if missing_deps:
        print(f"Missing dependencies: {', '.join(missing_deps)}")
        print("Please install required packages by running:")
        print("pip install -r requirements.txt")
        return False
    else:
        print("All dependencies are installed and working!")
        return True

if __name__ == "__main__":
    test_imports()