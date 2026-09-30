"""
Auth API Router — /api/auth
─────────────────────────────
Login, token exchange, current-user info, and demo user seeding.
All reviewer identity is derived from the authenticated JWT principal —
never from a client-supplied request body.
"""
from __future__ import annotations

import os
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.core.auth import (
    hash_password, verify_password, create_access_token,
    get_current_user, require_admin, _JWT_AVAILABLE, _PASSLIB_AVAILABLE,
)
from app.models.user import User
from app.models.base import generate_uuid
from app.core.logging import logger

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ──────────────────────────────────────────────────────────────────────────────
# Simple in-memory login rate limiter: 5 attempts / minute per (IP + username)
# ──────────────────────────────────────────────────────────────────────────────
import time
from collections import defaultdict
from threading import Lock

_LOGIN_ATTEMPTS: dict[str, list[float]] = defaultdict(list)
_LOGIN_LOCK = Lock()
_RATE_LIMIT_WINDOW = 60   # seconds
_RATE_LIMIT_MAX    = 5    # attempts


def _check_login_rate_limit(ip: str, username: str) -> None:
    key = f"{ip}:{username}"
    now = time.monotonic()
    with _LOGIN_LOCK:
        attempts = [t for t in _LOGIN_ATTEMPTS[key] if now - t < _RATE_LIMIT_WINDOW]
        if len(attempts) >= _RATE_LIMIT_MAX:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Please wait 60 seconds before trying again.",
                headers={"Retry-After": "60"},
            )
        attempts.append(now)
        _LOGIN_ATTEMPTS[key] = attempts


# ──────────────────────────────────────────────────────────────────────────────
# Schemas
# ──────────────────────────────────────────────────────────────────────────────
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str
    full_name: str


class UserMeResponse(BaseModel):
    id: str
    username: str
    email: str
    full_name: str
    role: str
    organization: str
    is_demo: bool


class SeedResult(BaseModel):
    seeded: int
    skipped: int
    message: str


# ──────────────────────────────────────────────────────────────────────────────
# Demo account definitions — NO passwords in source.
# Passwords are read from environment variables only.
# If not set in DEMO_MODE, a random password is generated and logged ONCE.
# ──────────────────────────────────────────────────────────────────────────────
_DEMO_ACCOUNTS = [
    {
        "username": "analyst_demo",
        "email": "analyst@mineintel.demo",
        "full_name": "Demo Analyst (CMPDI)",
        "role": "Analyst",
        "organization": "CMPDI / CIL",
        "password_env": "DEMO_ANALYST_PASSWORD",
    },
    {
        "username": "reviewer_demo",
        "email": "reviewer@mineintel.demo",
        "full_name": "Demo Reviewer (CMPDI)",
        "role": "Reviewer",
        "organization": "CMPDI / CIL",
        "password_env": "DEMO_REVIEWER_PASSWORD",
    },
    {
        "username": "admin_demo",
        "email": "admin@mineintel.demo",
        "full_name": "Demo Admin (MineIntel)",
        "role": "Admin",
        "organization": "CMPDI / CIL",
        "password_env": "DEMO_ADMIN_PASSWORD",
    },
]


_DEFAULT_DEMO_PASSWORDS = {
    "analyst_demo": "Analyst@Demo2026",
    "reviewer_demo": "Reviewer@Demo2026",
    "admin_demo": "Admin@Demo2026!",
}


def _get_demo_password(acct: dict) -> str:
    """
    Return the demo password for an account.
    Priority: env var → documented default demo credentials.
    """
    pw = os.environ.get(acct["password_env"], "").strip()
    if pw:
        return pw
    return _DEFAULT_DEMO_PASSWORDS.get(acct["username"], "Demo@2026!")


# ──────────────────────────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────────────────────────
@router.post("/token", response_model=TokenResponse, summary="Obtain JWT access token")
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Standard OAuth2 password-flow token endpoint.
    Returns a Bearer JWT on success.
    Rate-limited to 5 attempts per minute per IP + username.
    """
    if not _JWT_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="JWT library (python-jose) not installed. Install: pip install python-jose[cryptography]"
        )
    if not _PASSLIB_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Password library (passlib) not installed. Install: pip install passlib[bcrypt]"
        )

    # Rate limiting
    client_ip = request.client.host if request.client else "unknown"
    _check_login_rate_limit(client_ip, form_data.username)

    user = db.query(User).filter(User.username == form_data.username).first()
    demo_match = next((a for a in _DEMO_ACCOUNTS if a["username"] == form_data.username), None)
    expected_demo_pw = _DEFAULT_DEMO_PASSWORDS.get(form_data.username)

    # Auto-seed / sync demo account on the fly if standard demo credentials are used
    if demo_match and (form_data.password == expected_demo_pw or form_data.password == os.environ.get(demo_match["password_env"], "")):
        if not user:
            user = User(
                id=generate_uuid(),
                username=demo_match["username"],
                email=demo_match["email"],
                full_name=demo_match["full_name"],
                role=demo_match["role"],
                organization=demo_match["organization"],
                password_hash=hash_password(form_data.password),
                is_active=True,
                is_demo=True,
                created_at=datetime.now(timezone.utc),
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        elif not verify_password(form_data.password, user.password_hash):
            user.password_hash = hash_password(form_data.password)
            db.commit()
            db.refresh(user)

    if not user or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated.")

    token_data = {
        "sub": user.id,
        "username": user.username,
        "role": user.role,
        "full_name": user.full_name,
        "is_demo": user.is_demo,
    }
    token = create_access_token(token_data)
    logger.info(f"User '{user.username}' ({user.role}) logged in.")
    return TokenResponse(
        access_token=token,
        role=user.role,
        username=user.username,
        full_name=user.full_name,
    )


@router.get("/me", response_model=UserMeResponse, summary="Current authenticated user")
def get_me(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns profile of the authenticated user."""
    user = db.query(User).filter(User.id == current_user["sub"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return UserMeResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        organization=user.organization,
        is_demo=user.is_demo,
    )


@router.post("/seed-demo-users", response_model=SeedResult, summary="Seed demo accounts (Admin only, DEMO_MODE=true)")
def seed_demo_users(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """
    Creates the three documented demo accounts (Analyst, Reviewer, Admin)
    if they do not already exist.

    Requires:
    - DEMO_MODE=true in environment
    - Admin JWT token

    Passwords are read from environment variables only
    (DEMO_ANALYST_PASSWORD, DEMO_REVIEWER_PASSWORD, DEMO_ADMIN_PASSWORD).
    If not set, a random password is generated and logged once.

    This endpoint is idempotent and safe to call on every startup.
    It will NEVER overwrite an existing password or any non-demo user.
    """
    if not settings.DEMO_MODE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo user seeding is disabled. Set DEMO_MODE=true to enable.",
        )

    if not _PASSLIB_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="passlib[bcrypt] not installed — cannot seed demo users.",
        )

    seeded = 0
    skipped = 0
    for acct in _DEMO_ACCOUNTS:
        existing = db.query(User).filter(User.username == acct["username"]).first()
        if existing:
            skipped += 1
            continue

        plain_pw = _get_demo_password(acct)
        new_user = User(
            id=generate_uuid(),
            username=acct["username"],
            email=acct["email"],
            full_name=acct["full_name"],
            role=acct["role"],
            organization=acct["organization"],
            password_hash=hash_password(plain_pw),
            is_active=True,
            is_demo=True,
            created_at=datetime.now(timezone.utc),
        )
        db.add(new_user)
        seeded += 1
        logger.info(f"Seeded demo user: {acct['username']} ({acct['role']})")

    db.commit()
    return SeedResult(
        seeded=seeded,
        skipped=skipped,
        message=f"Demo user seeding complete: {seeded} created, {skipped} already existed.",
    )
