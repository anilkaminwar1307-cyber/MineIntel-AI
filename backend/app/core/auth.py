"""
MineIntel Authentication Service
─────────────────────────────────
Provides secure password hashing (bcrypt via passlib), JWT signing, and role
checking for the Analyst / Reviewer / Admin role hierarchy.

All secrets are loaded from environment variables via pydantic-settings.
No credentials are hardcoded here.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.logging import logger

# ──────────────────────────────────────────────────────────────────────────────
# Conditional imports — gracefully degrade if packages not yet installed
# ──────────────────────────────────────────────────────────────────────────────
try:
    from jose import JWTError, jwt
    _JWT_AVAILABLE = True
except ImportError:
    _JWT_AVAILABLE = False
    logger.warning("python-jose not installed — JWT authentication disabled. Run: pip install python-jose[cryptography]")

try:
    # Compatibility shim: passlib 1.7.4 reads bcrypt.__about__.__version__ which
    # was removed in bcrypt 4.x. Provide a shim so passlib can detect the version.
    import bcrypt as _bcrypt_mod
    if not hasattr(_bcrypt_mod, "__about__"):
        import types as _types
        _about = _types.SimpleNamespace(__version__=getattr(_bcrypt_mod, "__version__", "4.0.0"))
        _bcrypt_mod.__about__ = _about  # type: ignore[attr-defined]

    from passlib.context import CryptContext
    _pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    _PASSLIB_AVAILABLE = True
except ImportError:
    _pwd_context = None
    _PASSLIB_AVAILABLE = False
    logger.warning("passlib not installed — password hashing disabled. Run: pip install passlib[bcrypt]")


# ──────────────────────────────────────────────────────────────────────────────
from app.core.config import settings

# ──────────────────────────────────────────────────────────────────────────────
# Config (loaded from settings / environment)
# ──────────────────────────────────────────────────────────────────────────────
SECRET_KEY: str = settings.JWT_SECRET_KEY
ALGORITHM: str = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES: int = settings.JWT_EXPIRE_MINUTES

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)


# ──────────────────────────────────────────────────────────────────────────────
# Password helpers
# ──────────────────────────────────────────────────────────────────────────────
def hash_password(plain: str) -> str:
    """Return a bcrypt hash for *plain*. Raises RuntimeError if passlib unavailable."""
    if not _PASSLIB_AVAILABLE or _pwd_context is None:
        raise RuntimeError("passlib[bcrypt] is required for password hashing.")
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches *hashed*. Returns False if passlib unavailable."""
    if not _PASSLIB_AVAILABLE or _pwd_context is None:
        return False
    return _pwd_context.verify(plain, hashed)


# ──────────────────────────────────────────────────────────────────────────────
# JWT helpers
# ──────────────────────────────────────────────────────────────────────────────
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT access token."""
    if not _JWT_AVAILABLE:
        raise RuntimeError("python-jose[cryptography] is required for JWT.")
    if not SECRET_KEY:
        raise RuntimeError(
            "JWT_SECRET_KEY environment variable is not set. "
            "Add it to your .env file before enabling authentication."
        )
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Decode and verify a JWT. Returns None on any failure."""
    if not _JWT_AVAILABLE or not SECRET_KEY:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


# ──────────────────────────────────────────────────────────────────────────────
# FastAPI dependency — get current user from token (optional auth)
# ──────────────────────────────────────────────────────────────────────────────
def get_current_user_optional(token: Optional[str] = Depends(oauth2_scheme)) -> Optional[dict]:
    """
    Returns the decoded token payload (dict with sub, role, username, …)
    or None when no valid token is present.

    Use this for endpoints that degrade gracefully without auth.
    """
    if not token:
        return None
    return decode_token(token)


def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> dict:
    """
    Returns the decoded token payload.  Raises 401 when no valid token is present.
    Use this for protected endpoints.
    """
    payload = get_current_user_optional(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def require_role(*allowed_roles: str):
    """
    Dependency factory — enforces that the authenticated user has one of
    *allowed_roles*.  Example:
        @router.post("/approve")
        def approve(user=Depends(require_role("Reviewer", "Admin"))):
            ...
    """
    def _check(current_user: dict = Depends(get_current_user)) -> dict:
        role = current_user.get("role", "")
        if role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {' or '.join(allowed_roles)}. Your role: {role}",
            )
        return current_user
    return _check


# Convenience role guards
require_analyst = require_role("Analyst", "Reviewer", "Admin")
require_reviewer = require_role("Reviewer", "Admin")
require_admin    = require_role("Admin")
