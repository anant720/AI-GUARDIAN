

# Guardian/main.py

import argparse
import json
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

try:
    from . import detection
except ImportError:
    # Fallback for direct execution
    import detection

def main():
    """
    Main function to run the AI Guardian CLI.
    """
    parser = argparse.ArgumentParser(
        description="AI Guardian: Automatic Scam Detection for Messages."
    )
    parser.add_argument(
        "message",
        type=str,
        help="The message text to analyse."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output the result in JSON format."
    )

    args = parser.parse_args()

    # Analyse the message
    result = detection.analyse_message(args.message)

    # Print the result
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"--- AI Guardian Analysis ---")
        print(f"Risk Level: {result['level']} (Score: {result['score']})")
        if result['reasons']:
            print("\nReasons:")
            for reason in result['reasons']:
                print(f"- {reason}")
        if result.get('links'):
            print(f"\nLinks found: {', '.join(result['links'])}")
        print("--- End of Analysis ---")

if __name__ == "__main__":
    main()
