from pydantic import BaseModel
from typing import Optional, Dict, Any

class MessageIntelligence(BaseModel):
    intent: str
    urgency_score: float
    impersonated_brand: Optional[str] = None
    credential_request_detected: bool
    scam_probability: float
    scam_category: Optional[str] = None
    language: Optional[str] = None
    score_details: Optional[Dict[str, Any]] = None

class MessageIntelligenceReport(BaseModel):
    message_analysis: MessageIntelligence
