from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.core.auth import get_current_user_optional
from app.models.validation import ValidationIssue, EvidenceConflict
from app.models.fact import ExtractedFact
from app.models.document import Document
from app.models.review import ReviewAction
from app.models.audit import AuditEvent
from app.models.enums import ValidationStatus, AuditAction
from app.schemas.review import (
    ReviewQueueResponse, ReviewItemResponse, ConflictItemResponse,
    ReviewApproveRequest, ReviewRejectRequest, ReviewEditRequest, ConflictResolveRequest,
    FactEditAndApproveRequest
)

router = APIRouter(prefix="/reviews", tags=["Review Queue"])


def _resolve_reviewer(req_reviewer: str, current_user: Optional[dict]) -> str:
    """Return the reviewer identity from the JWT principal and enforce Reviewer/Admin RBAC;
    falls back to the request body value only for the unauthenticated demo flow."""
    if current_user and current_user.get("username"):
        role = current_user.get("role", "")
        if role and role not in ("Reviewer", "Admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Review verification and conflict resolution require Reviewer or Admin role. Your role: {role}",
            )
        return current_user["username"]
    return req_reviewer or "CMPDI Analyst"


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
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """
    Approves a fact, marking it as VERIFIED and recording human reviewer provenance.
    Reviewer identity is taken from the JWT principal when auth is enabled;
    falls back to the request body for the demo flow.
    """
    reviewer = _resolve_reviewer(req.reviewer_name, current_user)
    issue = db.query(ValidationIssue).filter(ValidationIssue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Validation issue not found.")

    fact = None
    if issue.fact_id:
        fact = db.query(ExtractedFact).filter(ExtractedFact.id == issue.fact_id).first()
        if fact:
            fact.validation_status = ValidationStatus.VERIFIED.value
            fact.human_verified = True
            fact.verified_by = reviewer
            fact.confidence_score = 1.0

    issue.is_resolved = True
    issue.resolved_by = reviewer
    issue.resolved_at = datetime.now(timezone.utc)

    # Log human review action
    action = ReviewAction(
        document_id=issue.document_id,
        fact_id=issue.fact_id,
        reviewer_name=reviewer,
        action="APPROVED",
        notes=req.notes
    )
    db.add(action)

    # Log immutable audit event
    audit = AuditEvent(
        user=reviewer,
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
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """
    Rejects a faulty extraction or spurious fact.
    """
    reviewer = _resolve_reviewer(req.reviewer_name, current_user)
    issue = db.query(ValidationIssue).filter(ValidationIssue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Validation issue not found.")

    if issue.fact_id:
        fact = db.query(ExtractedFact).filter(ExtractedFact.id == issue.fact_id).first()
        if fact:
            fact.validation_status = ValidationStatus.REJECTED.value

    issue.is_resolved = True
    issue.resolved_by = reviewer
    issue.resolved_at = datetime.now(timezone.utc)

    action = ReviewAction(
        document_id=issue.document_id,
        fact_id=issue.fact_id,
        reviewer_name=reviewer,
        action="REJECTED",
        notes=req.notes
    )
    db.add(action)

    audit = AuditEvent(
        user=reviewer,
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
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """
    Corrects a value and marks fact as VERIFIED with full audit logging.
    Preserves original extracted value in original_numeric_value.
    """
    issue = db.query(ValidationIssue).filter(ValidationIssue.id == issue_id).first()
    if not issue or not issue.fact_id:
        raise HTTPException(status_code=404, detail="Validation issue or related fact not found.")

    fact = db.query(ExtractedFact).filter(ExtractedFact.id == issue.fact_id).first()
    if not fact:
        raise HTTPException(status_code=404, detail="Fact not found.")

    new_val = req.get_value()
    prev_val = str(fact.numeric_value)
    prev_metric = fact.metric_code
    prev_unit = fact.unit
    prev_status = fact.validation_status

    # Preserve original extraction if not already set
    if fact.original_numeric_value is None:
        fact.original_numeric_value = fact.numeric_value
    if fact.original_metric_code is None:
        fact.original_metric_code = fact.metric_code
    if fact.original_unit is None:
        fact.original_unit = fact.unit

    reviewer = _resolve_reviewer(req.reviewer_name, current_user)

    # Apply updates
    fact.numeric_value = new_val
    if req.unit:
        fact.unit = req.unit
    if req.metric_code:
        fact.metric_code = req.metric_code
    if req.metric_name:
        fact.metric_name = req.metric_name
    if req.reporting_period:
        fact.reporting_period = req.reporting_period
    if req.subsidiary:
        fact.subsidiary = req.subsidiary
    if req.mine:
        fact.mine = req.mine
    if req.coalfield:
        fact.coalfield = req.coalfield

    fact.text_value = f"{new_val} {fact.unit or ''}"
    fact.validation_status = ValidationStatus.VERIFIED.value
    fact.human_verified = True
    fact.verified_by = reviewer
    fact.confidence_score = 1.0

    issue.is_resolved = True
    issue.resolved_by = reviewer
    issue.resolved_at = datetime.now(timezone.utc)

    action = ReviewAction(
        document_id=issue.document_id,
        fact_id=issue.fact_id,
        reviewer_name=reviewer,
        action="MODIFIED",
        previous_value=prev_val,
        new_value=str(new_val),
        previous_metric=prev_metric,
        new_metric=fact.metric_code,
        previous_unit=prev_unit,
        new_unit=fact.unit,
        previous_status=prev_status,
        new_status=ValidationStatus.VERIFIED.value,
        notes=req.notes
    )
    db.add(action)

    audit = AuditEvent(
        user=reviewer,
        action=AuditAction.FACT_EDITED.value,
        entity_type="FACT",
        entity_id=issue.fact_id,
        details=f"Analyst edited fact {issue.fact_id}: {prev_val} -> {new_val} {fact.unit}. Original value {fact.original_numeric_value} preserved. Status set to VERIFIED."
    )
    db.add(audit)
    db.commit()

    return {
        "message": "Fact modified and verified successfully",
        "issue_id": issue_id,
        "fact_id": fact.id,
        "new_value": new_val,
        "original_value": fact.original_numeric_value,
        "status": "VERIFIED"
    }


@router.post("/conflicts/{conflict_id}/resolve")
def resolve_evidence_conflict(
    conflict_id: str,
    req: ConflictResolveRequest,
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """
    Resolves a contradictory conflict between two evidence facts.
    Supports:
    - Version-aware: Mark newer version authoritative -> winning VERIFIED, losing SUPERSEDED
    - Accept chosen -> winning VERIFIED, losing REJECTED
    - Mark duplicate -> losing DUPLICATE
    - Override value -> updates value with analyst correction
    """
    reviewer = _resolve_reviewer(req.reviewer_name, current_user)
    conflict = db.query(EvidenceConflict).filter(EvidenceConflict.id == conflict_id).first()
    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict record not found.")

    winning_id = req.get_winning_id()
    winning_fact = db.query(ExtractedFact).filter(ExtractedFact.id == winning_id).first()
    if not winning_fact:
        raise HTTPException(status_code=404, detail="Winning fact not found.")

    losing_fact_id = conflict.conflicting_fact_id if winning_id == conflict.primary_fact_id else conflict.primary_fact_id
    losing_fact = db.query(ExtractedFact).filter(ExtractedFact.id == losing_fact_id).first()

    # Apply manual override value if provided
    if req.corrected_value is not None:
        if winning_fact.original_numeric_value is None:
            winning_fact.original_numeric_value = winning_fact.numeric_value
        winning_fact.numeric_value = req.corrected_value
        winning_fact.text_value = f"{req.corrected_value} {winning_fact.unit or ''}"

    winning_fact.validation_status = ValidationStatus.VERIFIED.value
    winning_fact.human_verified = True
    winning_fact.verified_by = reviewer
    winning_fact.confidence_score = 1.0

    action_label = "CONFLICT_RESOLVED"
    if losing_fact:
        if req.resolution_action == "MARK_SUPERSEDED" or "supersede" in req.resolution_notes.lower():
            losing_fact.validation_status = ValidationStatus.SUPERSEDED.value
            losing_fact.is_superseded = True
            losing_fact.superseded_by_id = winning_fact.id
            action_label = "SUPERSEDED"
        elif req.resolution_action == "MARK_DUPLICATE":
            losing_fact.validation_status = ValidationStatus.DUPLICATE.value
            action_label = "MARK_DUPLICATE"
        else:
            losing_fact.validation_status = ValidationStatus.REJECTED.value

    conflict.status = "RESOLVED"
    conflict.resolution_notes = req.resolution_notes
    conflict.resolved_by = reviewer
    conflict.resolved_at = datetime.now(timezone.utc)

    # Resolve related validation issues
    db.query(ValidationIssue).filter(
        ValidationIssue.fact_id.in_([conflict.primary_fact_id, conflict.conflicting_fact_id])
    ).update({"is_resolved": True, "resolved_by": reviewer, "resolved_at": datetime.now(timezone.utc)}, synchronize_session=False)

    action = ReviewAction(
        fact_id=winning_fact.id,
        conflict_id=conflict_id,
        reviewer_name=reviewer,
        action=action_label,
        previous_value=str(winning_fact.original_numeric_value or winning_fact.numeric_value),
        new_value=str(winning_fact.numeric_value),
        new_status="VERIFIED",
        notes=f"Resolved conflict {conflict_id} ({req.resolution_action}). Authoritative fact {winning_fact.id} confirmed. Notes: {req.resolution_notes}"
    )
    db.add(action)

    audit = AuditEvent(
        user=reviewer,
        action=AuditAction.CONFLICT_RESOLVED.value,
        entity_type="CONFLICT",
        entity_id=conflict_id,
        details=f"Conflict resolved ({action_label}): {winning_fact.metric_code} confirmed as {winning_fact.numeric_value} {winning_fact.unit} for {winning_fact.subsidiary} ({winning_fact.reporting_period})."
    )
    db.add(audit)
    db.commit()

    return {
        "message": "Conflict resolved successfully",
        "conflict_id": conflict_id,
        "winning_fact_id": winning_fact.id,
        "winning_value": winning_fact.numeric_value,
        "losing_fact_id": losing_fact_id,
        "losing_status": losing_fact.validation_status if losing_fact else "N/A",
        "status": "RESOLVED"
    }


@router.post("/facts/{fact_id}/approve")
def direct_approve_fact(
    fact_id: str,
    req: ReviewApproveRequest = ReviewApproveRequest(),
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """Directly verifies a fact from the Evidence Ledger or Evidence Drawer."""
    reviewer = _resolve_reviewer(req.reviewer_name, current_user)
    fact = db.query(ExtractedFact).filter(ExtractedFact.id == fact_id).first()
    if not fact:
        raise HTTPException(status_code=404, detail="Fact not found.")

    prev_status = fact.validation_status
    fact.validation_status = ValidationStatus.VERIFIED.value
    fact.human_verified = True
    fact.verified_by = reviewer
    # NOTE: Do NOT overwrite confidence_score here.
    # Extraction confidence is a separate field from human verification state.
    # Rule 6 (AGENTS.md): human_verified is set only by explicit analyst confirmation;
    # it does NOT retroactively make an extraction 100% confident.

    # Resolve any pending issues
    db.query(ValidationIssue).filter(ValidationIssue.fact_id == fact_id).update({
        "is_resolved": True,
        "resolved_by": reviewer,
        "resolved_at": datetime.now(timezone.utc)
    }, synchronize_session=False)

    action = ReviewAction(
        document_id=fact.document_id,
        fact_id=fact_id,
        reviewer_name=reviewer,
        action="APPROVED",
        previous_value=str(fact.numeric_value),
        new_value=str(fact.numeric_value),
        previous_status=prev_status,
        new_status=ValidationStatus.VERIFIED.value,
        notes=req.notes
    )
    db.add(action)

    audit = AuditEvent(
        user=reviewer,
        action=AuditAction.FACT_APPROVED.value,
        entity_type="FACT",
        entity_id=fact_id,
        details=f"Direct verification of fact {fact_id} ({fact.metric_name} = {fact.numeric_value} {fact.unit})."
    )
    db.add(audit)
    db.commit()

    return {"message": "Fact verified successfully", "fact_id": fact_id, "status": "VERIFIED"}


@router.post("/facts/{fact_id}/edit-and-approve")
def direct_edit_and_approve_fact(
    fact_id: str,
    req: FactEditAndApproveRequest,
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """
    Directly corrects and verifies a fact from Evidence Ledger or Evidence Drawer.
    Preserves original extraction and writes immutable ReviewAction + AuditEvent.
    """
    reviewer = _resolve_reviewer(req.reviewer_name, current_user)
    fact = db.query(ExtractedFact).filter(ExtractedFact.id == fact_id).first()
    if not fact:
        raise HTTPException(status_code=404, detail="Fact not found.")

    prev_val = str(fact.numeric_value)
    prev_metric = fact.metric_code
    prev_unit = fact.unit
    prev_status = fact.validation_status

    if fact.original_numeric_value is None:
        fact.original_numeric_value = fact.numeric_value
    if fact.original_metric_code is None:
        fact.original_metric_code = fact.metric_code
    if fact.original_unit is None:
        fact.original_unit = fact.unit

    fact.numeric_value = req.numeric_value
    if req.unit:
        fact.unit = req.unit
    if req.metric_code:
        fact.metric_code = req.metric_code
    if req.metric_name:
        fact.metric_name = req.metric_name
    if req.reporting_period:
        fact.reporting_period = req.reporting_period
    if req.subsidiary:
        fact.subsidiary = req.subsidiary
    if req.mine:
        fact.mine = req.mine
    if req.coalfield:
        fact.coalfield = req.coalfield
    if req.organization:
        fact.organization = req.organization

    fact.text_value = f"{req.numeric_value} {fact.unit or ''}"
    fact.validation_status = ValidationStatus.VERIFIED.value
    fact.human_verified = True
    fact.verified_by = reviewer
    fact.confidence_score = 1.0

    # Resolve any pending issues
    db.query(ValidationIssue).filter(ValidationIssue.fact_id == fact_id).update({
        "is_resolved": True,
        "resolved_by": reviewer,
        "resolved_at": datetime.now(timezone.utc)
    }, synchronize_session=False)

    action = ReviewAction(
        document_id=fact.document_id,
        fact_id=fact_id,
        reviewer_name=reviewer,
        action="MODIFIED",
        previous_value=prev_val,
        new_value=str(req.numeric_value),
        previous_metric=prev_metric,
        new_metric=fact.metric_code,
        previous_unit=prev_unit,
        new_unit=fact.unit,
        previous_status=prev_status,
        new_status=ValidationStatus.VERIFIED.value,
        notes=req.notes
    )
    db.add(action)

    audit = AuditEvent(
        user=reviewer,
        action=AuditAction.FACT_EDITED.value,
        entity_type="FACT",
        entity_id=fact_id,
        details=f"Analyst edited fact {fact_id}: {prev_val} -> {req.numeric_value} {fact.unit}. Original value {fact.original_numeric_value} retained. Status set to VERIFIED."
    )
    db.add(audit)
    db.commit()

    return {
        "message": "Fact corrected and verified successfully",
        "fact_id": fact_id,
        "numeric_value": fact.numeric_value,
        "original_numeric_value": fact.original_numeric_value,
        "status": "VERIFIED"
    }


@router.post("/facts/{fact_id}/supersede")
def supersede_fact(
    fact_id: str,
    superseded_by_id: str = Query(..., description="ID of authoritative fact"),
    reviewer_name: str = Query("CMPDI Analyst"),
    notes: str = Query("Marked as superseded by newer authoritative evidence"),
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """
    Marks an older fact as SUPERSEDED by a newer authoritative document fact.
    Both records are preserved.
    """
    reviewer = _resolve_reviewer(reviewer_name, current_user)
    old_fact = db.query(ExtractedFact).filter(ExtractedFact.id == fact_id).first()
    new_fact = db.query(ExtractedFact).filter(ExtractedFact.id == superseded_by_id).first()
    if not old_fact or not new_fact:
        raise HTTPException(status_code=404, detail="Source or authoritative fact not found.")

    old_fact.validation_status = ValidationStatus.SUPERSEDED.value
    old_fact.is_superseded = True
    old_fact.superseded_by_id = new_fact.id

    new_fact.validation_status = ValidationStatus.VERIFIED.value
    new_fact.human_verified = True
    new_fact.verified_by = reviewer

    action = ReviewAction(
        document_id=old_fact.document_id,
        fact_id=old_fact.id,
        reviewer_name=reviewer,
        action="SUPERSEDED",
        previous_value=str(old_fact.numeric_value),
        new_value=str(new_fact.numeric_value),
        previous_status=old_fact.validation_status,
        new_status=ValidationStatus.SUPERSEDED.value,
        notes=f"{notes}. Superseded by fact {new_fact.id} ({new_fact.numeric_value} {new_fact.unit})."
    )
    db.add(action)

    audit = AuditEvent(
        user=reviewer,
        action=AuditAction.FACT_SUPERSEDED.value,
        entity_type="FACT",
        entity_id=old_fact.id,
        details=f"Fact {old_fact.id} marked as superseded by authoritative fact {new_fact.id}."
    )
    db.add(audit)
    db.commit()

    return {
        "message": "Fact superseded successfully",
        "fact_id": old_fact.id,
        "superseded_by_id": new_fact.id,
        "old_status": "SUPERSEDED",
        "new_status": "VERIFIED"
    }


@router.post("/facts/{fact_id}/verify", summary="Verify a fact (alias for /approve)")
def verify_fact_alias(
    fact_id: str,
    req: ReviewApproveRequest = ReviewApproveRequest(),
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """
    Frontend-facing alias for POST /facts/{fact_id}/approve.
    The frontend calls /verify; this routes to the same logic.
    Reviewer identity should come from JWT in production — this endpoint
    accepts an optional reviewer_name for the demo flow only.
    """
    return direct_approve_fact(fact_id=fact_id, req=req, db=db, current_user=current_user)
