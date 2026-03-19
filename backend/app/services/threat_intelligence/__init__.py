"""
app/services/threat_intelligence/__init__.py
Public entry point: build_threat_report(url) -> dict
"""
from app.services.threat_intelligence.threat_report_builder import build_threat_report

__all__ = ["build_threat_report"]
