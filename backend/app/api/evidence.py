from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.models.fact import ExtractedFact
from app.models.document import Document
from app.models.enums import ValidationStatus
from app.schemas.fact import ExtractedFactResponse, ExtractedFactListResponse

router = APIRouter(prefix="/evidence", tags=["Evidence Ledger"])


@router.get("", response_model=ExtractedFactListResponse)
def get_evidence_ledger(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    metric: Optional[str] = None,
    period: Optional[str] = None,
    organization: Optional[str] = None,
    subsidiary: Optional[str] = None,
    document_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    min_confidence: Optional[float] = None
):
    """
    Query the Evidence Ledger with granular mining provenance filters.
    Returns database-backed verified facts without simulated or hallucinated numbers.
    """
    query = db.query(ExtractedFact)

    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            (ExtractedFact.metric_name.ilike(search_pattern)) |
            (ExtractedFact.metric_code.ilike(search_pattern)) |
            (ExtractedFact.mine.ilike(search_pattern)) |
            (ExtractedFact.coalfield.ilike(search_pattern)) |
            (ExtractedFact.source_context.ilike(search_pattern))
        )

    if metric:
        query = query.filter(ExtractedFact.metric_code == metric)

    if period:
        query = query.filter(ExtractedFact.reporting_period == period)

    if organization:
        query = query.filter(ExtractedFact.organization == organization)

    if subsidiary:
        query = query.filter(ExtractedFact.subsidiary == subsidiary)

    if document_id:
        query = query.filter(ExtractedFact.document_id == document_id)

    if status_filter:
        query = query.filter(ExtractedFact.validation_status == status_filter)

    if min_confidence is not None:
        query = query.filter(ExtractedFact.confidence_score >= min_confidence)

    total = query.count()

    verified_count = db.query(ExtractedFact).filter(
        ExtractedFact.validation_status == ValidationStatus.VERIFIED.value
    ).count()

    needs_review_count = db.query(ExtractedFact).filter(
        (ExtractedFact.validation_status == ValidationStatus.NEEDS_REVIEW.value) |
        (ExtractedFact.validation_status == ValidationStatus.REVIEW_REQUIRED.value)
    ).count()

    conflict_count = db.query(ExtractedFact).filter(
        ExtractedFact.validation_status == ValidationStatus.CONFLICT.value
    ).count()

    offset = (page - 1) * page_size
    items = query.order_by(desc(ExtractedFact.created_at)).offset(offset).limit(page_size).all()

    return ExtractedFactListResponse(
        items=[ExtractedFactResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        verified_count=verified_count,
        needs_review_count=needs_review_count,
        conflict_count=conflict_count
    )


@router.get("/{fact_id}", response_model=ExtractedFactResponse)
def get_fact(fact_id: str, db: Session = Depends(get_db)):
    """Retrieve an individual fact by its ID."""
    fact = db.query(ExtractedFact).filter(ExtractedFact.id == fact_id).first()
    if not fact:
        raise HTTPException(status_code=404, detail=f"Fact with ID '{fact_id}' not found.")
    return ExtractedFactResponse.model_validate(fact)


@router.get("/{fact_id}/source")
def get_fact_source_provenance(fact_id: str, db: Session = Depends(get_db)):
    """
    Retrieve deep provenance coordinates and source document information for a fact.
    Ensures Rule 2 compliance: every fact has traceable origin.
    """
    fact = db.query(ExtractedFact).filter(ExtractedFact.id == fact_id).first()
    if not fact:
        raise HTTPException(status_code=404, detail=f"Fact with ID '{fact_id}' not found.")

    doc = db.query(Document).filter(Document.id == fact.document_id).first()

    return {
        "fact_id": fact.id,
        "metric_code": fact.metric_code,
        "metric_name": fact.metric_name,
        "numeric_value": fact.numeric_value,
        "unit": fact.unit,
        "reporting_period": fact.reporting_period,
        "subsidiary": fact.subsidiary,
        "confidence_score": fact.confidence_score,
        "validation_status": fact.validation_status,
        "human_verified": fact.human_verified,
        "provenance": {
            "document_id": fact.document_id,
            "document_name": doc.original_filename if doc else "Unknown",
            "document_category": doc.document_category if doc else None,
            "page_number": fact.page_number,
            "sheet_name": fact.sheet_name,
            "row_number": fact.row_number,
            "column_name": fact.column_name,
            "cell_reference": fact.cell_reference,
            "table_reference": fact.table_reference,
            "source_context": fact.source_context,
            "extraction_method": fact.extraction_method,
        }
    }


# ─── Central Provenance Service Endpoints (EvidenceChain 2.0) ───────────────

@router.get("/{fact_id}/provenance", summary="Get universal fact provenance dossier")
def get_universal_provenance(fact_id: str, db: Session = Depends(get_db)):
    """
    Returns complete Sections A-H dossier for the universal EvidenceDrawer.
    """
    from app.services.evidence.provenance_service import ProvenanceService
    return ProvenanceService.get_fact_provenance(db, fact_id)


@router.get("/{fact_id}/context", summary="Get surrounding source preview")
def get_surrounding_source_context(fact_id: str, db: Session = Depends(get_db)):
    """
    Retrieves surrounding source document context:
    - Excel/CSV: surrounding table rows with highlighted cell
    - PDF: page text snippet with highlighted context
    - Missing source / legacy coordinates handling
    """
    from app.services.evidence.provenance_service import ProvenanceService
    return ProvenanceService.get_surrounding_source(db, fact_id)


@router.get("/{fact_id}/conflicts", summary="Get conflicts involving this fact")
def get_fact_conflicts(fact_id: str, db: Session = Depends(get_db)):
    """
    Returns any cross-document contradictions involving this fact.
    """
    from app.services.evidence.provenance_service import ProvenanceService
    return {"conflicts": ProvenanceService.get_related_conflicts(db, fact_id)}


@router.get("/{fact_id}/history", summary="Get immutable human review history")
def get_fact_review_history(fact_id: str, db: Session = Depends(get_db)):
    """
    Returns full chronological audit trail of human review actions on this fact.
    """
    from app.services.evidence.provenance_service import ProvenanceService
    return {"history": ProvenanceService.get_review_history(db, fact_id)}


@router.get("/{fact_id}/usage", summary="Get calculations and reports using this fact")
def get_fact_usage(fact_id: str, db: Session = Depends(get_db)):
    """
    Returns all calculations, reports, and queries where this fact is cited.
    """
    from app.services.evidence.provenance_service import ProvenanceService
    return ProvenanceService.get_usage_history(db, fact_id)


@router.get("/{fact_id}/related", summary="Get related entity and temporal evidence")
def get_related_evidence(fact_id: str, limit: int = Query(8, ge=1, le=25), db: Session = Depends(get_db)):
    """
    Returns related facts across entity hierarchy, adjacent periods, and complementary metrics.
    """
    from app.services.evidence.provenance_service import ProvenanceService
    return {"related": ProvenanceService.get_related_evidence(db, fact_id, limit=limit)}
