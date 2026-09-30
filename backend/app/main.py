import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.core.database import engine, Base
from app.core.logging import logger
from app.core.auth import require_analyst
import app.models  # Ensure all models are loaded for table creation

# Import Routers
from app.api.health import router as health_router
from app.api.system import router as system_router
from app.api.documents import router as documents_router
from app.api.evidence import router as evidence_router
from app.api.analytics import router as analytics_router
from app.api.reports import router as reports_router
from app.api.audit import router as audit_router
from app.api.reviews import router as reviews_router
from app.api.topics import router as topics_router
from app.api.query import router as query_router
from app.api.settings import router as settings_router
from app.api.calculations import router as calculations_router
from app.api.minegraph import router as minegraph_router
from app.api.parliamentary import router as parliamentary_router
from app.api.auth import router as auth_router
from app.api.data_quality import router as data_quality_router
from app.api.intelligence import router as intelligence_router



@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup and shutdown lifecycle handler.
    Initializes database tables on start.
    """
    logger.info("Initializing MineIntel backend...")
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection verified.")
    except Exception as e:
        logger.warning(f"Database connection check notice: {e}")

    # Auto-seed demo users when DEMO_MODE is enabled (idempotent, uses internal call)
    if settings.DEMO_MODE:
        try:
            from app.core.database import SessionLocal as _SL
            from app.api.auth import _DEMO_ACCOUNTS, _get_demo_password
            from app.core.auth import hash_password, _PASSLIB_AVAILABLE
            from app.models.user import User
            from app.models.base import generate_uuid
            from datetime import datetime, timezone
            if _PASSLIB_AVAILABLE:
                _sess = _SL()
                try:
                    for acct in _DEMO_ACCOUNTS:
                        existing = _sess.query(User).filter(User.username == acct["username"]).first()
                        if not existing:
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
                            _sess.add(new_user)
                    _sess.commit()
                finally:
                    _sess.close()
        except Exception as _e:
            logger.warning(f"Demo user seeding skipped: {_e}")

    yield

    logger.info("MineIntel backend shutting down...")


app = FastAPI(
    title="MineIntel API",
    description=(
        "Evidence Intelligence for Mining & Geological Operations.\n"
        "AI-Powered Geological, Mining and other Reporting Solution for CMPDI/CIL subsidiaries.\n"
        "Ministry of Coal / Coal India Limited (Problem Statement ID: 26023)."
    ),
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS for Frontend connectivity
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Public routers (no auth required) ──────────────────────────────────────────
app.include_router(health_router, prefix=settings.API_PREFIX)
# /api/auth/token (login) is public; /api/auth/me and /api/auth/seed-demo-users
# carry their own per-endpoint auth dependencies declared inside auth.py
app.include_router(auth_router, prefix=settings.API_PREFIX)

# /api/system endpoints are public (capability matrix, no sensitive data)
app.include_router(system_router, prefix=settings.API_PREFIX)

# ── Protected routers: require at minimum Analyst role ─────────────────────────
_analyst_dep = [Depends(require_analyst)]

app.include_router(documents_router,    prefix=settings.API_PREFIX, dependencies=_analyst_dep)
app.include_router(evidence_router,     prefix=settings.API_PREFIX, dependencies=_analyst_dep)
app.include_router(analytics_router,    prefix=settings.API_PREFIX, dependencies=_analyst_dep)
app.include_router(reports_router,      prefix=settings.API_PREFIX, dependencies=_analyst_dep)
app.include_router(audit_router,        prefix=settings.API_PREFIX, dependencies=_analyst_dep)
app.include_router(reviews_router,      prefix=settings.API_PREFIX, dependencies=_analyst_dep)
app.include_router(topics_router,       prefix=settings.API_PREFIX, dependencies=_analyst_dep)
app.include_router(query_router,        prefix=settings.API_PREFIX, dependencies=_analyst_dep)
app.include_router(intelligence_router, prefix=settings.API_PREFIX, dependencies=_analyst_dep)
app.include_router(settings_router,     prefix=settings.API_PREFIX, dependencies=_analyst_dep)
app.include_router(calculations_router, prefix=settings.API_PREFIX, dependencies=_analyst_dep)
app.include_router(minegraph_router,    prefix=settings.API_PREFIX, dependencies=_analyst_dep)
app.include_router(parliamentary_router,prefix=settings.API_PREFIX, dependencies=_analyst_dep)
app.include_router(data_quality_router, prefix=settings.API_PREFIX, dependencies=_analyst_dep)


@app.get("/", include_in_schema=False)
def root():
    """Redirect root path to interactive Swagger documentation."""
    return RedirectResponse(url="/docs")
