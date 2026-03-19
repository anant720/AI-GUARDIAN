"""
phase9/report_manager.py
─────────────────────────
Aggregates automated test results and generates structural (JSON) and
presentation (HTML) reports inside logs/test_reports/.
"""
import os
import json
from datetime import datetime, timezone
from typing import Dict, Any, List

REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "logs", "test_reports")

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def generate_test_report(tests: List[Dict[str, Any]], overall_pass: bool) -> str:
    """
    Takes a list of test results and generates an HTML and JSON report.
    Returns the path to the HTML report.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"report_{timestamp}"
    json_path = os.path.join(REPORT_DIR, f"{base_name}.json")
    html_path = os.path.join(REPORT_DIR, f"{base_name}.html")

    # 1. Write JSON
    report_data = {
        "timestamp": _utc_now(),
        "overall_status": "PASS" if overall_pass else "FAIL",
        "total_tests": len(tests),
        "passed_tests": sum(1 for t in tests if t.get("status") == "PASS"),
        "failed_tests": sum(1 for t in tests if t.get("status") == "FAIL"),
        "results": tests
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=4)

    # 2. Write HTML
    status_color = "green" if overall_pass else "red"
    html_content = f"""
    <html>
    <head>
        <title>AI Guardian Test Report</title>
        <style>
            body {{ font-family: sans-serif; margin: 2rem; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            .pass {{ color: green; font-weight: bold; }}
            .fail {{ color: red; font-weight: bold; }}
        </style>
    </head>
    <body>
        <h1>AI Guardian Automated Test Report</h1>
        <h3>Overview</h3>
        <p><strong>Time:</strong> {report_data['timestamp']}</p>
        <p><strong>Overall Status:</strong> <span style="color: {status_color}; font-weight: bold;">{report_data['overall_status']}</span></p>
        <p><strong>Total Tests:</strong> {report_data['total_tests']} 
           (Passed: {report_data['passed_tests']}, Failed: {report_data['failed_tests']})</p>
        
        <h3>Test Results</h3>
        <table>
            <tr>
                <th>Test Name</th>
                <th>Type</th>
                <th>Status</th>
                <th>Message / Error</th>
                <th>Duration (ms)</th>
            </tr>
    """
    
    for t in tests:
        cls = "pass" if t.get("status") == "PASS" else "fail"
        html_content += f"""
            <tr>
                <td>{t.get("name", "Unknown")}</td>
                <td>{t.get("type", "Unknown")}</td>
                <td class="{cls}">{t.get("status", "FAIL")}</td>
                <td>{t.get("message", "-")}</td>
                <td>{t.get("duration_ms", 0)}</td>
            </tr>
        """
        
    html_content += """
        </table>
    </body>
    </html>
    """
    
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return os.path.abspath(html_path)

def get_latest_report() -> Dict[str, Any]:
    """Finds and returns the JSON payload of the most recent report."""
    try:
        files = [f for f in os.listdir(REPORT_DIR) if f.endswith(".json")]
        if not files:
            return {"error": "No reports found"}
        
        # Sort chronologically by filename scheme report_YYYYMMDD_HHMMSS.json
        latest_file = sorted(files)[-1]
        with open(os.path.join(REPORT_DIR, latest_file), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"error": f"Failed to read report: {e}"}
