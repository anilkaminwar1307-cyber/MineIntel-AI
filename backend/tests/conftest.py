import sys
import os
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone

# Add backend directory to sys.path
backend_dir = str(Path(__file__).parent.parent.resolve())
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy.pool import StaticPool
import app.models  # Ensure all models are registered with Base.metadata
from app.core.database import Base
from app.core.auth import create_access_token, hash_password, _PASSLIB_AVAILABLE
from app.models.user import User
from app.models.base import generate_uuid


# ── Shared JWT token factories ────────────────────────────────────────────────

def make_analyst_token() -> str:
    """Return a valid Analyst JWT without hitting the DB."""
    return create_access_token({
        "sub": "test-analyst-id",
        "username": "test_analyst",
        "role": "Analyst",
        "full_name": "Test Analyst",
    })


def make_reviewer_token() -> str:
    return create_access_token({
        "sub": "test-reviewer-id",
        "username": "test_reviewer",
        "role": "Reviewer",
        "full_name": "Test Reviewer",
    })


def make_admin_token() -> str:
    return create_access_token({
        "sub": "test-admin-id",
        "username": "test_admin",
        "role": "Admin",
        "full_name": "Test Admin",
    })


def analyst_headers() -> dict:
    return {"Authorization": f"Bearer {make_analyst_token()}"}


def reviewer_headers() -> dict:
    return {"Authorization": f"Bearer {make_reviewer_token()}"}


def admin_headers() -> dict:
    return {"Authorization": f"Bearer {make_admin_token()}"}


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def db_session():
    """Provides a fresh SQLite in-memory database session for each test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_db(db_session):
    """Alias for db_session fixture."""
    return db_session


@pytest.fixture
def analyst_token() -> str:
    return make_analyst_token()


@pytest.fixture
def reviewer_token() -> str:
    return make_reviewer_token()


@pytest.fixture
def admin_token() -> str:
    return make_admin_token()


@pytest.fixture
def auth_headers(analyst_token) -> dict:
    """Default auth headers (Analyst role) for use in tests that just need auth."""
    return {"Authorization": f"Bearer {analyst_token}"}


@pytest.fixture
def admin_auth_headers(admin_token) -> dict:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def reviewer_auth_headers(reviewer_token) -> dict:
    return {"Authorization": f"Bearer {reviewer_token}"}
