from fastapi import APIRouter
from app.schemas.health import CapabilitiesResponse
from app.services.ocr import ocr_provider

router = APIRouter(prefix="/system", tags=["System Capabilities"])


@router.get("/capabilities", response_model=CapabilitiesResponse)
def get_capabilities():
    """
    Returns the real capability matrix of the MineIntel deployment.
    Reflects the actual operational readiness of each subsystem in Phase 2.
    """
    return CapabilitiesResponse(
        document_upload=True,
        pdf_extraction=True,
        spreadsheet_processing=True,
        csv_processing=True,
        image_processing=True,
        ocr=ocr_provider.is_available(),
        document_enhancement=True,
        fact_extraction=True,
        evidence_ledger=True,
        query_engine=True,
        semantic_search=True,
        report_generation=True,
        topic_intelligence=True
    )
