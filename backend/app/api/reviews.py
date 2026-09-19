from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.models.validation import ValidationIssue, EvidenceConflict
from app.models.fact import ExtractedFact
from app.models.document import Document
from app.models.review import ReviewAction
from app.models.audit import AuditEvent
from app.models.enums import ValidationStatus, AuditAction
from app.schemas.review import (
    ReviewQueueResponse, ReviewItemResponse, ConflictItemResponse,
    ReviewApproveRequest, ReviewRejectRequest, ReviewEditRequest, ConflictResolveRequest
)

router = APIRouter(prefix="/reviews", tags=["Review Queue"])


@router.get("", response_model=ReviewQueueResponse)
def get_review_queue(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    severity: Optional[str] = None,
    issue_type: Optional[str] = None,
    document_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Returns items requiring human verification or conflict resolution.
    Supports filtering by severity, issue type, document, and server-side pagination.
    """
    query = db.query(ValidationIssue).filter(ValidationIssue.is_resolved == False)

    if severity and severity != "ALL":
        query = query.filter(ValidationIssue.severity == severity)

    if issue_type and issue_type != "ALL":
        query = query.filter(ValidationIssue.issue_type == issue_type)

    if document_id:
        query = query.filter(ValidationIssue.document_id == document_id)

    total = query.count()
    offset = (page - 1) * page_size
    open_issues = query.order_by(desc(ValidationIssue.created_at)).offset(offset).limit(page_size).all()

    open_conflicts_cnt = db.query(EvidenceConflict).filter(EvidenceConflict.status == "OPEN").count()
    low_confidence_cnt = db.query(ExtractedFact).filter(
        (ExtractedFact.confidence_score < 0.75) |
        (ExtractedFact.validation_status.in_([ValidationStatus.NEEDS_REVIEW.value, ValidationStatus.REVIEW_REQUIRED.value]))
    ).count()

    # Pre-fetch fact and document references
    fact_ids = [iss.fact_id for iss in open_issues if iss.fact_id]
    doc_ids = [iss.document_id for iss in open_issues if iss.document_id]

    facts_map = {f.id: f for f in db.query(ExtractedFact).filter(ExtractedFact.id.in_(fact_ids)).all()} if fact_ids else {}
    docs_map = {d.id: d.original_filename for d in db.query(Document).filter(Document.id.in_(doc_ids)).all()} if doc_ids else {}

    review_items = []
    for issue in open_issues:
        f = facts_map.get(issue.fact_id)
        review_items.append(ReviewItemResponse(
            id=issue.id,
            document_id=issue.document_id,
            fact_id=issue.fact_id,
            issue_type=issue.issue_type,
            severity=issue.severity,
            description=issue.description,
            is_resolved=issue.is_resolved,
            created_at=issue.created_at,
            metric_name=f.metric_name if f else None,
            numeric_value=f.numeric_value if f else None,
            unit=f.unit if f else None,
            subsidiary=f.subsidiary if f else None,
            reporting_period=f.reporting_period if f else None,
            confidence_score=f.confidence_score if f else None,
            source_reference=f.cell_reference or (f"Page {f.page_number}" if f and f.page_number else None) if f else None,
            document_name=docs_map.get(issue.document_id, "Document")
        ))

    # Fetch conflicts list for UI conflict tab
    conflicts_list = []
    conflict_rows = db.query(EvidenceConflict).filter(EvidenceConflict.status == "OPEN").order_by(desc(EvidenceConflict.created_at)).limit(25).all()
    
    conflict_fact_ids = []
    for c in conflict_rows:
        conflict_fact_ids.extend([c.primary_fact_id, c.conflicting_fact_id])
    
    c_facts_map = {f.id: f for f in db.query(ExtractedFact).filter(ExtractedFact.id.in_(conflict_fact_ids)).all()} if conflict_fact_ids else {}

    for c in conflict_rows:
        pf = c_facts_map.get(c.primary_fact_id)
        cf = c_facts_map.get(c.conflicting_fact_id)
        conflicts_list.append(ConflictItemResponse(
            id=c.id,
            metric_code=c.metric_code,
            primary_fact_id=c.primary_fact_id,
            conflicting_fact_id=c.conflicting_fact_id,
            description=c.description,
            discrepancy_percent=c.discrepancy_percent,
            status=c.status,
            created_at=c.created_at,
            primary_value=f"{pf.numeric_value} {pf.unit}" if pf else "N/A",
            conflicting_value=f"{cf.numeric_value} {cf.unit}" if cf else "N/A",
            subsidiary=pf.subsidiary if pf else (cf.subsidiary if cf else None),
            period=pf.reporting_period if pf else (cf.reporting_period if cf else None)
        ))

    return ReviewQueueResponse(
        open_reviews=total,
        conflicts=open_conflicts_cnt,
        low_confidence=low_confidence_cnt,
        missing_metadata=0,
        total=total,
        page=page,
        page_size=page_size,
        items=review_items,
        conflict_items=conflicts_list
    )


@router.get("/conflicts")
def get_conflicts_list(db: Session = Depends(get_db)):
    """
    Returns the list of active cross-document contradictory conflicts.
    """
    conflict_rows = db.query(EvidenceConflict).filter(EvidenceConflict.status == "OPEN").order_by(desc(EvidenceConflict.created_at)).limit(50).all()
    
    conflict_fact_ids = []
    for c in conflict_rows:
        conflict_fact_ids.extend([c.primary_fact_id, c.conflicting_fact_id])
    
    c_facts_map = {f.id: f for f in db.query(ExtractedFact).filter(ExtractedFact.id.in_(conflict_fact_ids)).all()} if conflict_fact_ids else {}
    
    conflicts_out = []
    for c in conflict_rows:
        pf = c_facts_map.get(c.primary_fact_id)
        cf = c_facts_map.get(c.conflicting_fact_id)
        conflicts_out.append({
            "id": c.id,
            "metric_code": c.metric_code,
            "subsidiary": pf.subsidiary if pf else (cf.subsidiary if cf else "CIL"),
            "reporting_period": pf.reporting_period if pf else (cf.reporting_period if cf else "N/A"),
            "fact_a_id": c.primary_fact_id,
            "fact_a_value": pf.numeric_value if pf else 0.0,
            "fact_a_doc": pf.source_context or "Official Subsidiary Monthly Review" if pf else "Document A",
            "fact_b_id": c.conflicting_fact_id,
            "fact_b_value": cf.numeric_value if cf else 0.0,
            "fact_b_doc": cf.source_context or "Annual Operating Plan / Provisional" if cf else "Document B",
            "discrepancy_pct": c.discrepancy_percent or 5.0,
            "status": c.status,
            "detected_at": c.created_at.isoformat() if c.created_at else ""
        })
    
    return {"conflicts": conflicts_out, "total": len(conflicts_out)}


@router.post("/{issue_id}/approve")
def approve_review_item(
    issue_id: str,
    req: ReviewApproveRequest = ReviewApproveRequest(),
    db: Session = Depends(get_db)
):
    """
    Approves a fact, marking it as VERIFIED and recording human reviewer provenance.
    Immediately updates database, audit log, and resolves the validation issue.
    """
    issue = db.query(ValidationIssue).filter(ValidationIssue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Validation issue not found.")

    fact = None
    if issue.fact_id:
        fact = db.query(ExtractedFact).filter(ExtractedFact.id == issue.fact_id).first()
        if fact:
            fact.validation_status = ValidationStatus.VERIFIED.value
            fact.human_verified = True
            fact.verified_by = req.reviewer_name
            fact.confidence_score = 1.0

    issue.is_resolved = True
    issue.resolved_by = req.reviewer_name
    issue.resolved_at = datetime.utcnow()

    # Log human review action
    action = ReviewAction(
        document_id=issue.document_id,
        fact_id=issue.fact_id,
        reviewer_name=req.reviewer_name,
        action="APPROVED",
        notes=req.notes
    )
    db.add(action)

    # Log immutable audit event
    audit = AuditEvent(
        user=req.reviewer_name,
        action=AuditAction.FACT_APPROVED.value,
        entity_type="FACT",
        entity_id=issue.fact_id,
        details=f"Analyst approved fact {issue.fact_id} ({fact.metric_name if fact else 'Metric'} = {fact.numeric_value if fact else ''}). Notes: {req.notes}"
    )
    db.add(audit)
    db.commit()

    return {"message": "Fact approved successfully", "issue_id": issue_id, "fact_id": issue.fact_id, "status": "VERIFIED"}


@router.post("/{issue_id}/reject")
def reject_review_item(
    issue_id: str,
    req: ReviewRejectRequest = ReviewRejectRequest(),
    db: Session = Depends(get_db)
):
    """
    Rejects a faulty extraction or spurious fact.
    """
    issue = db.query(ValidationIssue).filter(ValidationIssue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Validation issue not found.")

    if issue.fact_id:
        fact = db.query(ExtractedFact).filter(ExtractedFact.id == issue.fact_id).first()
        if fact:
            fact.validation_status = ValidationStatus.REJECTED.value

    issue.is_resolved = True
    issue.resolved_by = req.reviewer_name
    issue.resolved_at = datetime.utcnow()

    action = ReviewAction(
        document_id=issue.document_id,
        fact_id=issue.fact_id,
        reviewer_name=req.reviewer_name,
        action="REJECTED",
        notes=req.notes
    )
    db.add(action)

    audit = AuditEvent(
        user=req.reviewer_name,
        action=AuditAction.FACT_REJECTED.value,
        entity_type="FACT",
        entity_id=issue.fact_id,
        details=f"Analyst rejected fact {issue.fact_id}. Reason: {req.notes}"
    )
    db.add(audit)
    db.commit()

    return {"message": "Fact rejected successfully", "issue_id": issue_id, "status": "REJECTED"}


@router.post("/{issue_id}/edit-and-approve")
def edit_and_approve_review_item(
    issue_id: str,
    req: ReviewEditRequest,
    db: Session = Depends(get_db)
):
    """
    Corrects a value and marks fact as VERIFIED with full audit logging.
    """
    issue = db.query(ValidationIssue).filter(ValidationIssue.id == issue_id).first()
    if not issue or not issue.fact_id:
        raise HTTPException(status_code=404, detail="Validation issue or related fact not found.")

    fact = db.query(ExtractedFact).filter(ExtractedFact.id == issue.fact_id).first()
    if not fact:
        raise HTTPException(status_code=404, detail="Fact not found.")

    new_val = req.get_value()
    prev_val = str(fact.numeric_value)
    fact.numeric_value = new_val
    fact.text_value = f"{new_val} {req.unit or fact.unit or ''}"
    if req.unit:
        fact.unit = req.unit
    fact.validation_status = ValidationStatus.VERIFIED.value
    fact.human_verified = True
    fact.verified_by = req.reviewer_name
    fact.confidence_score = 1.0

    issue.is_resolved = True
    issue.resolved_by = req.reviewer_name
    issue.resolved_at = datetime.utcnow()

    action = ReviewAction(
        document_id=issue.document_id,
        fact_id=issue.fact_id,
        reviewer_name=req.reviewer_name,
        action="MODIFIED",
        previous_value=prev_val,
        new_value=str(new_val),
        notes=req.notes
    )
    db.add(action)

    audit = AuditEvent(
        user=req.reviewer_name,
        action=AuditAction.FACT_EDITED.value,
        entity_type="FACT",
        entity_id=issue.fact_id,
        details=f"Analyst edited fact {issue.fact_id}: {prev_val} -> {new_val}. Status set to VERIFIED."
    )
    db.add(audit)
    db.commit()

    return {"message": "Fact modified and verified successfully", "issue_id": issue_id, "new_value": new_val, "status": "VERIFIED"}


@router.post("/conflicts/{conflict_id}/resolve")
def resolve_evidence_conflict(
    conflict_id: str,
    req: ConflictResolveRequest,
    db: Session = Depends(get_db)
):
    """
    Resolves a contradictory conflict between two evidence facts.
    The selected fact is confirmed as VERIFIED, while the alternative is marked REJECTED / SUPERSEDED.
    """
    conflict = db.query(EvidenceConflict).filter(EvidenceConflict.id == conflict_id).first()
    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict record not found.")

    winning_id = req.get_winning_id()
    winning_fact = db.query(ExtractedFact).filter(ExtractedFact.id == winning_id).first()
    if not winning_fact:
        raise HTTPException(status_code=404, detail="Winning fact not found.")

    losing_fact_id = conflict.conflicting_fact_id if winning_id == conflict.primary_fact_id else conflict.primary_fact_id
    losing_fact = db.query(ExtractedFact).filter(ExtractedFact.id == losing_fact_id).first()

    winning_fact.validation_status = ValidationStatus.VERIFIED.value
    winning_fact.human_verified = True
    winning_fact.verified_by = req.reviewer_name

    if losing_fact:
        losing_fact.validation_status = ValidationStatus.REJECTED.value

    conflict.status = "RESOLVED"
    conflict.resolution_notes = req.resolution_notes
    conflict.resolved_by = req.reviewer_name
    conflict.resolved_at = datetime.utcnow()

    # Resolve related validation issues
    db.query(ValidationIssue).filter(
        ValidationIssue.fact_id.in_([conflict.primary_fact_id, conflict.conflicting_fact_id])
    ).update({"is_resolved": True, "resolved_by": req.reviewer_name, "resolved_at": datetime.utcnow()}, synchronize_session=False)

    action = ReviewAction(
        fact_id=winning_fact.id,
        reviewer_name=req.reviewer_name,
        action="CONFLICT_RESOLVED",
        notes=f"Resolved conflict {conflict_id}. Preferred fact {winning_fact.id} ({winning_fact.numeric_value}). Notes: {req.resolution_notes}"
    )
    db.add(action)

    audit = AuditEvent(
        user=req.reviewer_name,
        action=AuditAction.FACT_APPROVED.value,
        entity_type="CONFLICT",
        entity_id=conflict_id,
        details=f"Conflict resolved: {winning_fact.metric_code} confirmed as {winning_fact.numeric_value} {winning_fact.unit} for {winning_fact.subsidiary} ({winning_fact.reporting_period})."
    )
    db.add(audit)
    db.commit()

    return {
        "message": "Conflict resolved successfully",
        "conflict_id": conflict_id,
        "winning_fact_id": winning_fact.id,
        "winning_value": winning_fact.numeric_value,
        "status": "RESOLVED"
    }


@router.post("/facts/{fact_id}/approve")
def direct_approve_fact(
    fact_id: str,
    req: ReviewApproveRequest = ReviewApproveRequest(),
    db: Session = Depends(get_db)
):
    """Directly verifies a fact from the Evidence Ledger."""
    fact = db.query(ExtractedFact).filter(ExtractedFact.id == fact_id).first()
    if not fact:
        raise HTTPException(status_code=404, detail="Fact not found.")

    fact.validation_status = ValidationStatus.VERIFIED.value
    fact.human_verified = True
    fact.verified_by = req.reviewer_name
    fact.confidence_score = 1.0

    # Resolve any pending issues
    db.query(ValidationIssue).filter(ValidationIssue.fact_id == fact_id).update({
        "is_resolved": True,
        "resolved_by": req.reviewer_name,
        "resolved_at": datetime.utcnow()
    }, synchronize_session=False)

    audit = AuditEvent(
        user=req.reviewer_name,
        action=AuditAction.FACT_APPROVED.value,
        entity_type="FACT",
        entity_id=fact_id,
        details=f"Direct verification of fact {fact_id} ({fact.metric_name} = {fact.numeric_value} {fact.unit})."
    )
    db.add(audit)
    db.commit()

    return {"message": "Fact verified successfully", "fact_id": fact_id, "status": "VERIFIED"}

