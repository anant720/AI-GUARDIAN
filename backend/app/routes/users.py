"""
app/routes/users.py — Phase 7 Auth Endpoints
──────────────────────────────────────────────
POST /users/signup  — create account, return JWT
POST /users/login   — authenticate, return JWT
"""
import asyncio
from fastapi import APIRouter, HTTPException, status

from app.logger import logger
from app.services.database.db import get_conn, is_connected
from app.services.database.auth import hash_password, verify_password, create_jwt
from app.services.database.schemas import SignupRequest, LoginRequest, TokenResponse
from app.services.monitoring.db_diagnostics import collect_env_and_dump
from app.services.monitoring.self_heal import orchestrate_self_healing

router = APIRouter(prefix="/users", tags=["users"])


def _db_required(bypass: bool = False):
    if not is_connected() and not bypass:
        try:
            asyncio.create_task(asyncio.to_thread(collect_env_and_dump))
            asyncio.create_task(orchestrate_self_healing("postgres"))
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not configured. Add DATABASE_URL to .env"
        )


# ── POST /users/signup ─────────────────────────────────────────────────────────
@router.post("/signup", response_model=TokenResponse, status_code=201)
async def signup(req: SignupRequest):
    """
    Create a new user account.
    Returns JWT token for immediate use.
    """
    _db_required()
    hashed = hash_password(req.password)

    try:
        async with get_conn() as conn:
            # Check for duplicate
            existing = await conn.fetchrow(
                "SELECT user_id FROM users WHERE username=$1 OR email=$2",
                req.username, req.email
            )
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Username or email already registered"
                )

            # Insert user
            row = await conn.fetchrow(
                """INSERT INTO users (username, email, hashed_password, role)
                   VALUES ($1, $2, $3, $4)
                   RETURNING user_id, username, role""",
                req.username, req.email, hashed, req.role
            )

            # Default permissions
            await conn.execute(
                "INSERT INTO user_permissions (user_id) VALUES ($1) ON CONFLICT DO NOTHING",
                row["user_id"]
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Signup failed: {e}")
        raise HTTPException(status_code=500, detail="Signup failed")

    token = create_jwt(row["user_id"], row["role"], row["username"])
    logger.info(f"New user registered: {row['username']} (role={row['role']})")
    return TokenResponse(
        user_id=row["user_id"],
        username=row["username"],
        role=row["role"],
        token=token
    )


# ── POST /users/login ─────────────────────────────────────────────────────────
@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    """
    Authenticate an existing user.
    Returns JWT token.
    """
    _db_required()

    try:
        async with get_conn() as conn:
            row = await conn.fetchrow(
                "SELECT user_id, username, hashed_password, role "
                "FROM users WHERE username=$1 OR email=$1",
                req.username
            )
    except Exception as e:
        logger.error(f"Login DB error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

    if not row or not verify_password(req.password, row["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    # Update last_login
    try:
        async with get_conn() as conn:
            await conn.execute(
                "UPDATE users SET last_login=NOW() WHERE user_id=$1",
                row["user_id"]
            )
    except Exception:
        pass

    token = create_jwt(row["user_id"], row["role"], row["username"])
    logger.info(f"User logged in: {row['username']}")
    return TokenResponse(
        user_id=row["user_id"],
        username=row["username"],
        role=row["role"],
        token=token
    )
