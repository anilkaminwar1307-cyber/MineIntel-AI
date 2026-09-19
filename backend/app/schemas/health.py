from typing import Literal, Optional
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "error"] = "ok"
    database: Literal["connected", "error", "disconnected"] = "connected"
    storage: Literal["available", "error", "unavailable"] = "available"
    gemini: Literal["configured", "not_configured"] = "not_configured"
    version: str = "0.2.0"
    app_name: str = "MineIntel"


class CapabilitiesResponse(BaseModel):
    document_upload: bool = True
    pdf_extraction: bool = True
    spreadsheet_processing: bool = True
    csv_processing: bool = True
    image_processing: bool = True
    ocr: bool = False
    document_enhancement: bool = True
    fact_extraction: bool = True
    evidence_ledger: bool = True
    query_engine: bool = True
    semantic_search: bool = True
    report_generation: bool = True
    topic_intelligence: bool = True
    review_workflow: bool = True
    analytics: bool = True

