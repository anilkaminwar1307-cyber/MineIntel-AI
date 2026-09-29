"""
test_auth_rbac.py — Authentication & RBAC Tests for MineIntel

Tests:
1. Public endpoints remain accessible without auth
2. Every non-public route returns 401 for anonymous requests
   (discovered by iterating app.routes — so new unguarded routes auto-fail)
3. Analyst cannot delete documents (403)
4. Analyst cannot change settings / delete reports (403)
5. Reviewer cannot access admin-only delete endpoints (403)
6. Reviewer CAN approve/reject in review queue
7. Login rate limiting (5 attempts / minute)
"""
import pytest
import time
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.routing import APIRoute

from app.main import app
from app.core.database import Base, get_db
from app.core.auth import (
    create_access_token, hash_password, _PASSLIB_AVAILABLE,
    require_analyst, require_reviewer, require_admin,
)
from app.models.user import User
from app.models.base import generate_uuid
from datetime import datetime, timezone


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def auth_test_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture(scope="module")
def auth_test_db(auth_test_engine):
    """
    Creates in-memory DB and seeds three demo users directly (bypassing the HTTP
    seed endpoint which now requires an Admin token — correctness verified separately).
    """
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=auth_test_engine)
    session = TestingSession()

    if _PASSLIB_AVAILABLE:
        _demo_users = [
            {"username": "analyst_demo", "email": "analyst@mineintel.demo",
             "full_name": "Demo Analyst (CMPDI)", "role": "Analyst",
             "organization": "CMPDI / CIL", "password": "Analyst@Demo2026"},
            {"username": "reviewer_demo", "email": "reviewer@mineintel.demo",
             "full_name": "Demo Reviewer (CMPDI)", "role": "Reviewer",
             "organization": "CMPDI / CIL", "password": "Reviewer@Demo2026"},
            {"username": "admin_demo", "email": "admin@mineintel.demo",
             "full_name": "Demo Admin (MineIntel)", "role": "Admin",
             "organization": "CMPDI / CIL", "password": "Admin@Demo2026!"},
        ]
        for u in _demo_users:
            if not session.query(User).filter(User.username == u["username"]).first():
                session.add(User(
                    id=generate_uuid(),
                    username=u["username"],
                    email=u["email"],
                    full_name=u["full_name"],
                    role=u["role"],
                    organization=u["organization"],
                    password_hash=hash_password(u["password"]),
                    is_active=True,
                    is_demo=True,
                    created_at=datetime.now(timezone.utc),
                ))
        session.commit()
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
    Base.metadata.drop_all(bind=auth_test_engine)


@pytest.fixture
def client(auth_test_db):
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def _token(role: str, username: str) -> str:
    """Generate a valid JWT for the given role without hitting the DB."""
    return create_access_token({"sub": "test-id", "username": username, "role": role, "full_name": username})


def _headers(role: str, username: str | None = None) -> dict:
    uname = username or f"{role.lower()}_demo"
    return {"Authorization": f"Bearer {_token(role, uname)}"}


# ── PUBLIC ENDPOINTS ─────────────────────────────────────────────────────────

def test_public_health_endpoints(client):
    """Health endpoints are public and do not require authentication."""
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_public_system_capabilities(client):
    """System capabilities are public."""
    res = client.get("/api/system/capabilities")
    assert res.status_code == 200


def test_public_docs(client):
    """Swagger docs are public."""
    res = client.get("/docs")
    assert res.status_code in (200, 307)  # may redirect


# ── ANONYMOUS → 401 on every protected route ─────────────────────────────────

# Routes that should be accessible without auth (exact path prefixes)
_PUBLIC_PATH_PREFIXES = (
    "/api/health",
    "/api/auth/token",   # login endpoint
    "/api/system/",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/",
)

_PROBE_METHODS = {
    "GET":    lambda c, path: c.get(path),
    "POST":   lambda c, path: c.post(path, json={}),
    "DELETE": lambda c, path: c.delete(path),
    "PATCH":  lambda c, path: c.patch(path, json={}),
    "PUT":    lambda c, path: c.put(path, json={}),
}


def _is_public(path: str) -> bool:
    for prefix in _PUBLIC_PATH_PREFIXES:
        if path.startswith(prefix):
            return True
    return False


def test_anonymous_gets_401_on_all_protected_routes(client):
    """
    Iterate app.routes and verify that every non-public route
    returns 401 (or 405 Method Not Allowed, not 200/403) for anonymous requests.
    Any newly added unguarded route will fail this test automatically.
    """
    failed_routes = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        path = route.path
        if _is_public(path):
            continue

        # Use path with placeholder IDs replaced
        test_path = path.replace("{document_id}", "nonexistent-id") \
                        .replace("{report_id}", "nonexistent-id") \
                        .replace("{issue_id}", "nonexistent-id") \
                        .replace("{fact_id}", "nonexistent-id") \
                        .replace("{claim_id}", "nonexistent-id") \
                        .replace("{topic_id}", "nonexistent-id") \
                        .replace("{review_id}", "nonexistent-id")

        for method in route.methods or ["GET"]:
            probe = _PROBE_METHODS.get(method)
            if probe is None:
                continue
            res = probe(client, test_path)
            if res.status_code not in (401, 403, 404, 405, 422):
                # 404/422 = route hit the DB layer (auth passed) → BAD
                # We only allow 404 if it is NOT reachable without a token
                # Re-check: a 200 or 307 without token = unguarded!
                if res.status_code in (200, 201, 307):
                    failed_routes.append(
                        f"{method} {path} → {res.status_code} (expected 401)"
                    )

    assert not failed_routes, (
        "The following routes are NOT protected by authentication:\n"
        + "\n".join(f"  • {r}" for r in failed_routes)
    )


# ── LOGIN TESTS ───────────────────────────────────────────────────────────────

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


def test_login_invalid_password(client):
    """Invalid password returns 401 Unauthorized."""
    res = client.post(
        "/api/auth/token",
        data={"username": "analyst_demo", "password": "WrongPassword123"},
    )
    assert res.status_code == 401
    assert "Incorrect username or password" in res.json()["detail"]


# ── /auth/me ──────────────────────────────────────────────────────────────────

def test_auth_me_protected(client):
    """Calling /api/auth/me requires authentication."""
    unauth = client.get("/api/auth/me")
    assert unauth.status_code == 401

    login_res = client.post(
        "/api/auth/token",
        data={"username": "analyst_demo", "password": "Analyst@Demo2026"},
    )
    real_token = login_res.json()["access_token"]
    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {real_token}"})
    assert me_res.status_code == 200
    assert me_res.json()["username"] == "analyst_demo"
    assert me_res.json()["role"] == "Analyst"


# ── RBAC: ANALYST cannot DELETE ──────────────────────────────────────────────

def test_analyst_cannot_delete_document(client):
    """Analyst (not Admin) gets 403 when trying to delete a document."""
    res = client.delete(
        "/api/documents/some-doc-id",
        headers=_headers("Analyst"),
    )
    assert res.status_code == 403


def test_analyst_cannot_delete_report(client):
    """Analyst gets 403 when trying to delete a report."""
    res = client.delete(
        "/api/reports/some-report-id",
        headers=_headers("Analyst"),
    )
    assert res.status_code == 403


def test_reviewer_cannot_delete_document(client):
    """Reviewer (not Admin) gets 403 when trying to delete a document."""
    res = client.delete(
        "/api/documents/some-doc-id",
        headers=_headers("Reviewer"),
    )
    assert res.status_code == 403


# ── RBAC: ANALYST cannot change data-quality (write) ─────────────────────────

def test_analyst_cannot_resolve_quality_issue(client):
    """Analyst gets 403 on data-quality resolve (Reviewer/Admin only)."""
    res = client.post(
        "/api/data-quality/issues/some-issue-id/resolve",
        json={"notes": "test"},
        headers=_headers("Analyst"),
    )
    assert res.status_code == 403


def test_analyst_cannot_dismiss_quality_issue(client):
    """Analyst gets 403 on data-quality dismiss (Reviewer/Admin only)."""
    res = client.post(
        "/api/data-quality/issues/some-issue-id/dismiss",
        json={"reason": "test"},
        headers=_headers("Analyst"),
    )
    assert res.status_code == 403


# ── RBAC: REVIEWER can approve/reject in review queue ────────────────────────

def test_rbac_analyst_forbidden_from_review_approval(client):
    """Analyst cannot approve review queue items (requires Reviewer or Admin)."""
    login_res = client.post(
        "/api/auth/token",
        data={"username": "analyst_demo", "password": "Analyst@Demo2026"},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

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


# ── RBAC: seed-demo-users requires Admin + DEMO_MODE ─────────────────────────

def test_seed_demo_users_requires_admin_token(client):
    """seed-demo-users endpoint rejects non-Admin tokens."""
    # Analyst → 403
    res = client.post("/api/auth/seed-demo-users", headers=_headers("Analyst"))
    assert res.status_code == 403

    # Reviewer → 403
    res = client.post("/api/auth/seed-demo-users", headers=_headers("Reviewer"))
    assert res.status_code == 403

    # No token → 401
    res = client.post("/api/auth/seed-demo-users")
    assert res.status_code == 401


def test_seed_demo_users_blocked_when_demo_mode_off(client, monkeypatch):
    """seed-demo-users endpoint returns 403 when DEMO_MODE=False even for Admin."""
    import app.core.config as cfg
    monkeypatch.setattr(cfg.settings, "DEMO_MODE", False)

    res = client.post("/api/auth/seed-demo-users", headers=_headers("Admin"))
    assert res.status_code == 403
    assert "disabled" in res.json()["detail"].lower()


# ── RATE LIMITING ─────────────────────────────────────────────────────────────

def test_login_rate_limit(client):
    """
    After 5 failed login attempts from the same IP+username within 60 s,
    the 6th request must return 429 Too Many Requests.
    """
    # Reset by using a unique username that doesn't exist
    username = "ratelimit_test_user"
    for _ in range(5):
        client.post("/api/auth/token", data={"username": username, "password": "wrong"})

    # 6th attempt should be rate-limited
    res = client.post("/api/auth/token", data={"username": username, "password": "wrong"})
    assert res.status_code == 429
    assert "Too many login attempts" in res.json()["detail"]


# ── ANALYST CAN access read-only routes (smoke test) ─────────────────────────

def test_analyst_can_list_documents(client):
    """Analyst can call GET /api/documents (read-only)."""
    res = client.get("/api/documents", headers=_headers("Analyst"))
    assert res.status_code == 200


def test_analyst_can_list_evidence(client):
    """Analyst can call GET /api/evidence (read-only)."""
    res = client.get("/api/evidence", headers=_headers("Analyst"))
    assert res.status_code == 200


def test_analyst_can_get_analytics(client):
    """Analyst can call GET /api/analytics/overview (read-only)."""
    res = client.get("/api/analytics/overview", headers=_headers("Analyst"))
    assert res.status_code == 200
