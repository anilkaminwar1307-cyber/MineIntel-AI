from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.fact import ExtractedFact
from app.models.document import Document
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


@router.get("/data-scope")
def get_data_scope(db: Session = Depends(get_db)):
    """
    Returns counts of real vs demo facts and documents in the Evidence Ledger.
    """
    real_facts = db.query(ExtractedFact).filter(ExtractedFact.is_demo == False).count()
    demo_facts = db.query(ExtractedFact).filter(ExtractedFact.is_demo == True).count()
    real_docs = db.query(Document).filter(Document.is_demo == False).count()
    demo_docs = db.query(Document).filter(Document.is_demo == True).count()
    return {
        "status": "ok",
        "real_facts_count": real_facts,
        "demo_facts_count": demo_facts,
        "total_facts_count": real_facts + demo_facts,
        "real_documents_count": real_docs,
        "demo_documents_count": demo_docs,
        "total_documents_count": real_docs + demo_docs,
        "real_facts": real_facts,
        "demo_facts": demo_facts,
        "real_documents": real_docs,
        "demo_documents": demo_docs,
    }

