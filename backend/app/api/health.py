from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.core.config import settings
from app.schemas.health import HealthResponse
from app.providers.ai.gemini import get_ai_provider
from app.services.storage.local import storage_service
from pathlib import Path

router = APIRouter(tags=["Health & Status"])


@router.get("/health", response_model=HealthResponse)
def get_health(db: Session = Depends(get_db)):
    """
    Returns platform health, database connectivity, storage status, and Gemini AI status.
    Never exposes internal secrets.
    """
    # 1. Check Database
    db_status = "disconnected"
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "error"

    # 2. Check Storage
    storage_status = "available" if storage_service.base_dir.exists() else "unavailable"

    # 3. Check Gemini
    ai_provider = get_ai_provider()
    gemini_info = ai_provider.get_status()
    gemini_status = gemini_info.get("status", "not_configured")

    overall_status = "ok" if db_status == "connected" and storage_status == "available" else "degraded"

    return HealthResponse(
        status=overall_status,
        database=db_status,
        storage=storage_status,
        gemini=gemini_status,
        version=settings.VERSION,
        app_name=settings.APP_NAME
    )
