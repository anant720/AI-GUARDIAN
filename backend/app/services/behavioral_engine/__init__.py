"""
behavioral_engine/__init__.py
Exposes: run_behavioral_analysis(...) -> BehavioralReport
"""
from app.services.behavioral_engine.ai_behavioral_risk_engine import run_behavioral_analysis

__all__ = ["run_behavioral_analysis"]
