"""
behavioral_analysis/__init__.py
Public entry point: analyze_behavior(message, url) -> BehaviorReport dict
"""
import asyncio
from typing import Dict, Any

from app.services.behavioral_analysis.sequence_analyzer import analyze_sequences
from app.services.behavioral_analysis.timing_detector import detect_time_pressure
from app.services.behavioral_analysis.interaction_history_checker import check_interaction_history


async def analyze_behavior(message: str = "", url: str = "") -> Dict[str, Any]:
    """
    Run all behavioral analysis checks concurrently.

    Returns consolidated BehaviorReport with a behavioral_risk_score (0-100).
    """
    seq, timing, history = await asyncio.gather(
        asyncio.to_thread(analyze_sequences, message),
        asyncio.to_thread(detect_time_pressure, message),
        check_interaction_history(message, url)
    )

    # Compute composite behavioral risk score
    urgency_pts  = int(timing.get("severity", 0) * 30)   # max 30
    manip_pts    = int(seq.get("urgency_score", 0) * 40)  # max 40
    anomaly_pts  = 20 if history.get("anomaly_detected") else 0

    behavioral_risk_score = min(urgency_pts + manip_pts + anomaly_pts, 100)

    return {
        "sequence_analysis": seq,
        "timing_analysis": timing,
        "interaction_history": history,
        "behavioral_risk_score": behavioral_risk_score
    }


__all__ = ["analyze_behavior"]
