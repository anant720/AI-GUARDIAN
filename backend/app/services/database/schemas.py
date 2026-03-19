"""
phase7/schemas.py — Pydantic v2 models for all Phase 7 API routes
"""
from typing import Optional, Any, Dict, List
from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime


# ── Auth ──────────────────────────────────────────────────────────────────────
class SignupRequest(BaseModel):
    username:  str = Field(..., min_length=3, max_length=50)
    email:     EmailStr
    password:  str = Field(..., min_length=8)
    role:      str = Field(default="user")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        allowed = {"user", "analyst", "admin"}
        if v not in allowed:
            raise ValueError(f"role must be one of {allowed}")
        return v


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    user_id:  int
    username: str
    role:     str
    token:    str


class UserProfile(BaseModel):
    user_id:    int
    username:   str
    email:      str
    role:       str
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None


# ── Notification logging ───────────────────────────────────────────────────────
class NotificationLogRequest(BaseModel):
    app_name:         str = Field(..., max_length=100, description="e.g. Gmail, WhatsApp")
    message_text:     Optional[str] = None
    url:              Optional[str] = None
    # Optional: caller may pre-scan or let POST /notifications run Phase 1-6
    risk_score:       Optional[int] = Field(default=None, ge=0, le=100)
    scam_probability: Optional[int] = Field(default=None, ge=0, le=100)
    phase5_behavior:  Optional[Dict[str, Any]] = None
    llm_verdict:      Optional[Dict[str, Any]] = None


class NotificationLogResponse(BaseModel):
    notification_id:  int
    user_id:          int
    scam_probability: int
    risk_score:       int
    phase3_reasoning: Optional[str] = None
    phase4_threat_intel: Optional[Dict[str, Any]] = None
    phase5_behavioral_analysis: Optional[Dict[str, Any]] = None
    logging:          Dict[str, Any] = Field(default_factory=dict)
    scan_result:      Optional[Dict[str, Any]] = None


# ── Interaction ───────────────────────────────────────────────────────────────
class InteractionRequest(BaseModel):
    notification_id: int
    action_type:     str

    @field_validator("action_type")
    @classmethod
    def validate_action(cls, v: str) -> str:
        allowed = {"read", "clicked", "ignored"}
        if v not in allowed:
            raise ValueError(f"action_type must be one of {allowed}")
        return v


class InteractionResponse(BaseModel):
    interaction_id:  int
    notification_id: int
    action_type:     str


# ── Dashboard ─────────────────────────────────────────────────────────────────
class NotificationSummary(BaseModel):
    notification_id:  int
    app_name:         Optional[str]
    url:              Optional[str]
    risk_score:       int
    scam_probability: int
    created_at:       Optional[datetime]


class UserStatsResponse(BaseModel):
    user_id:             int
    username:            str
    total_notifications: int
    scam_notifications:  int
    avg_risk_score:      float
    recent:              List[NotificationSummary] = []


class AppStatsItem(BaseModel):
    app_name:               str
    total_notifications:    int
    high_risk_notifications: int
    last_updated:           Optional[datetime]


class AppStatsResponse(BaseModel):
    apps:  List[AppStatsItem]
    total: int
