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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup and shutdown lifecycle handler.
    Initializes database tables on start.
    """
    logger.info("Initializing MineIntel backend...")
    try:
        Base.metadata.create_all(bind=engine)
        # Migrate generated_reports columns if missing
        from sqlalchemy import text
        with engine.connect() as conn:
            res = conn.execute(text("PRAGMA table_info(generated_reports)")).fetchall()
            col_names = [r[1] for r in res]
            if col_names:
                if "pdf_status" not in col_names:
                    conn.execute(text("ALTER TABLE generated_reports ADD COLUMN pdf_status VARCHAR(50) DEFAULT 'READY'"))
                if "pdf_path" not in col_names:
                    conn.execute(text("ALTER TABLE generated_reports ADD COLUMN pdf_path VARCHAR(500)"))
                if "pdf_filename" not in col_names:
                    conn.execute(text("ALTER TABLE generated_reports ADD COLUMN pdf_filename VARCHAR(255)"))
                if "pdf_size" not in col_names:
                    conn.execute(text("ALTER TABLE generated_reports ADD COLUMN pdf_size INTEGER DEFAULT 0"))
                if "pdf_generated_at" not in col_names:
                    conn.execute(text("ALTER TABLE generated_reports ADD COLUMN pdf_generated_at DATETIME"))
                conn.commit()
        logger.info("Database tables and columns verified / created successfully.")
    except Exception as e:
        logger.error(f"Error creating database tables / migrating: {e}")

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


@app.get("/", include_in_schema=False)
def root():
    """Redirect root path to interactive Swagger documentation."""
    return RedirectResponse(url="/docs")
