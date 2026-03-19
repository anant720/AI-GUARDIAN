"""
phase7/auth.py — JWT + bcrypt authentication + RBAC
─────────────────────────────────────────────────────
• hash_password / verify_password  (bcrypt via passlib)
• create_jwt / decode_jwt          (HS256 via PyJWT)
• get_current_user                 (FastAPI Depends)
• require_role                     (RBAC dependency factory)
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

import jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.logger import logger

# -- Password settings (Bypassing broken passlib) --

# ── JWT settings ──────────────────────────────────────────────────────────────
_SECRET     = os.getenv("JWT_SECRET_KEY", "")
_ALGORITHM  = "HS256"
_EXPIRE_HRS = int(os.getenv("JWT_EXPIRE_HOURS", "12"))

_bearer = HTTPBearer(auto_error=True)


# ── Password helpers ──────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


# ── JWT helpers ───────────────────────────────────────────────────────────────
def create_jwt(user_id: int, role: str, username: str) -> str:
    if not _SECRET:
        raise RuntimeError("JWT_SECRET_KEY not configured in .env")
    payload = {
        "user_id":  user_id,
        "role":     role,
        "username": username,
        "exp":      datetime.now(timezone.utc) + timedelta(hours=_EXPIRE_HRS)
    }
    return jwt.encode(payload, _SECRET, algorithm=_ALGORITHM)


def decode_jwt(token: str) -> Dict[str, Any]:
    if not _SECRET:
        raise RuntimeError("JWT_SECRET_KEY not configured in .env")
    try:
        return jwt.decode(token, _SECRET, algorithms=[_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}"
        )


# ── FastAPI dependency: current user from Bearer token ────────────────────────
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer)
) -> Dict[str, Any]:
    """
    FastAPI dependency. Extracts and validates JWT from Authorization header.

    Returns decoded payload: {user_id, role, username}
    """
    return decode_jwt(credentials.credentials)


# ── RBAC dependency factory ───────────────────────────────────────────────────
def require_role(*allowed_roles: str):
    """
    Factory returning a FastAPI dependency that enforces role access.

    Usage:
        @router.get("/admin/...", dependencies=[Depends(require_role("admin"))])
    """
    async def _check(
        user: Dict[str, Any] = Depends(get_current_user)
    ) -> Dict[str, Any]:
        if user.get("role") not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role: {' or '.join(allowed_roles)}"
            )
        return user
    return _check
