import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.core.database import engine, Base
from app.core.logging import logger
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup and shutdown lifecycle handler.
    Initializes database tables on start.
    """
    logger.info("Initializing MineIntel backend...")
    try:
        from alembic.config import Config
        from alembic import command
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        alembic_ini_path = os.path.join(backend_dir, "alembic.ini")
        if os.path.exists(alembic_ini_path):
            alembic_cfg = Config(alembic_ini_path)
            alembic_cfg.set_main_option("script_location", os.path.join(backend_dir, "migrations"))
            command.upgrade(alembic_cfg, "head")
            logger.info("Database schema verified via Alembic migrations.")
        else:
            Base.metadata.create_all(bind=engine)
            logger.info("Database schema initialized via metadata.")
    except Exception as e:
        logger.warning(f"Alembic auto-migration notice: {e}, falling back to create_all()")
        Base.metadata.create_all(bind=engine)


    # Auto-seed demo users when DEMO_MODE is enabled (idempotent)
    if settings.DEMO_MODE:
        try:
            from app.core.database import SessionLocal as _SL
            from app.api.auth import _DEMO_ACCOUNTS, seed_demo_users
            _sess = _SL()
            seed_demo_users(db=_sess)
            _sess.close()
        except Exception as _e:
            logger.warning(f"Demo user seeding skipped (passlib not installed or other error): {_e}")

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

# Mount API Routers
app.include_router(health_router, prefix=settings.API_PREFIX)
app.include_router(system_router, prefix=settings.API_PREFIX)
app.include_router(documents_router, prefix=settings.API_PREFIX)
app.include_router(evidence_router, prefix=settings.API_PREFIX)
app.include_router(analytics_router, prefix=settings.API_PREFIX)
app.include_router(reports_router, prefix=settings.API_PREFIX)
app.include_router(audit_router, prefix=settings.API_PREFIX)
app.include_router(reviews_router, prefix=settings.API_PREFIX)
app.include_router(topics_router, prefix=settings.API_PREFIX)
app.include_router(query_router, prefix=settings.API_PREFIX)
app.include_router(settings_router, prefix=settings.API_PREFIX)
app.include_router(calculations_router, prefix=settings.API_PREFIX)
app.include_router(minegraph_router, prefix=settings.API_PREFIX)
app.include_router(parliamentary_router, prefix=settings.API_PREFIX)
app.include_router(auth_router, prefix=settings.API_PREFIX)


@app.get("/", include_in_schema=False)
def root():
    """Redirect root path to interactive Swagger documentation."""
    return RedirectResponse(url="/docs")
