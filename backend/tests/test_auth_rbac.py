import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.api.auth import seed_demo_users
from app.core.auth import create_access_token


@pytest.fixture(scope="module")
def auth_test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSession()
    # Seed demo accounts
    seed_demo_users(session)
    session.close()

    def _override_get_db():
        s = TestingSession()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(auth_test_db):
    with TestClient(app) as c:
        yield c


def test_public_health_endpoints(client):
    """Health endpoints are public and do not require authentication."""
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_login_analyst_success(client):
    """Analyst demo login yields valid JWT token."""
    res = client.post(
        "/api/auth/token",
        data={"username": "analyst_demo", "password": "Analyst@Demo2026"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["role"] == "Analyst"
    assert data["username"] == "analyst_demo"


def test_login_reviewer_success(client):
    """Reviewer demo login yields valid JWT token."""
    res = client.post(
        "/api/auth/token",
        data={"username": "reviewer_demo", "password": "Reviewer@Demo2026"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["role"] == "Reviewer"
    assert data["username"] == "reviewer_demo"


def test_login_admin_success(client):
    """Admin demo login yields valid JWT token."""
    res = client.post(
        "/api/auth/token",
        data={"username": "admin_demo", "password": "Admin@Demo2026!"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["role"] == "Admin"
    assert data["username"] == "admin_demo"


def test_login_invalid_password(client):
    """Invalid password returns 401 Unauthorized."""
    res = client.post(
        "/api/auth/token",
        data={"username": "analyst_demo", "password": "WrongPassword123"},
    )
    assert res.status_code == 401
    assert "Incorrect username or password" in res.json()["detail"]


def test_auth_me_protected(client):
    """Calling /api/auth/me requires authentication."""
    # Unauthenticated
    unauth = client.get("/api/auth/me")
    assert unauth.status_code == 401

    # Authenticated Analyst
    token = create_access_token({"sub": "test-id-1", "username": "analyst_demo", "role": "Analyst"})
    auth_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    # Since sub test-id-1 might not match db user, let's get actual user token
    login_res = client.post(
        "/api/auth/token",
        data={"username": "analyst_demo", "password": "Analyst@Demo2026"},
    )
    real_token = login_res.json()["access_token"]
    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {real_token}"})
    assert me_res.status_code == 200
    assert me_res.json()["username"] == "analyst_demo"
    assert me_res.json()["role"] == "Analyst"


def test_rbac_analyst_forbidden_from_review_approval(client):
    """Analyst cannot approve review queue items (requires Reviewer or Admin)."""
    login_res = client.post(
        "/api/auth/token",
        data={"username": "analyst_demo", "password": "Analyst@Demo2026"},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to approve a dummy issue
    res = client.post("/api/reviews/dummy-issue-id/approve", json={}, headers=headers)
    assert res.status_code == 403
    assert "require Reviewer or Admin role" in res.json()["detail"]


def test_rbac_reviewer_allowed_for_review_approval(client):
    """Reviewer role passes RBAC check on review endpoints (fails only on missing issue ID)."""
    login_res = client.post(
        "/api/auth/token",
        data={"username": "reviewer_demo", "password": "Reviewer@Demo2026"},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Calling with nonexistent issue id should pass RBAC and return 404, NOT 403
    res = client.post("/api/reviews/nonexistent-issue/approve", json={}, headers=headers)
    assert res.status_code == 404
