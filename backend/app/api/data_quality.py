"""
Data Quality API — MineIntel Phase 2
Endpoints for listing, filtering, assigning, resolving, and summarising
ValidationIssues and EvidenceConflicts.

All write operations enforce Reviewer/Admin RBAC.
"""
from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, case, or_

from app.core.database import get_db
from app.core.auth import require_analyst, require_reviewer
from app.models.validation import ValidationIssue, EvidenceConflict
from app.models.document import Document

router = APIRouter(prefix="/data-quality", tags=["Data Quality"])


# ── helpers ──────────────────────────────────────────────────────────────────


def _format_dt(dt) -> Optional[str]:
    if dt is None:
        return None
    if isinstance(dt, str):
        return dt
    if hasattr(dt, "isoformat"):
        return dt.isoformat()
    return str(dt)


def _issue_to_dict(issue: ValidationIssue) -> dict:
    return {
        "id": issue.id,
        "document_id": issue.document_id,
        "fact_id": issue.fact_id,
        "issue_type": issue.issue_type,
        "severity": issue.severity,
        "description": issue.description,
        "status": issue.status,
        "assigned_to": issue.assigned_to,
        "mine": issue.mine,
        "subsidiary": issue.subsidiary,
        "reporting_period": issue.reporting_period,
        "metric_code": issue.metric_code,
        "previous_value": issue.previous_value,
        "proposed_value": issue.proposed_value,
        "previous_unit": issue.previous_unit,
        "proposed_unit": issue.proposed_unit,
        "reviewer_comments": issue.reviewer_comments,
        "evidence_context": issue.evidence_context,
        "is_resolved": bool(issue.is_resolved),
        "resolved_by": issue.resolved_by,
        "resolved_at": _format_dt(issue.resolved_at),
        "created_at": _format_dt(issue.created_at),
    }


# ── read endpoints (any authenticated user) ───────────────────────────────────

@router.get("/issues")
def list_issues(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    severity: Optional[str] = Query(None, description="LOW|MEDIUM|HIGH|CRITICAL"),
    status_filter: Optional[str] = Query(None, alias="status"),
    issue_type: Optional[str] = None,
    subsidiary: Optional[str] = None,
    document_id: Optional[str] = None,
    is_resolved: Optional[bool] = None,
    q: Optional[str] = Query(None, description="Search query"),
    search: Optional[str] = Query(None, description="Search query alias"),
    db: Session = Depends(get_db),
):
    """
    List data-quality issues with rich server-side filtering and pagination.
    """
    try:
        query = db.query(ValidationIssue)

        if severity and severity != "ALL":
            query = query.filter(ValidationIssue.severity == severity)
        if status_filter and status_filter != "ALL":
            query = query.filter(ValidationIssue.status == status_filter)
        if issue_type and issue_type != "ALL":
            query = query.filter(ValidationIssue.issue_type == issue_type)
        if subsidiary:
            query = query.filter(ValidationIssue.subsidiary == subsidiary)
        if document_id:
            query = query.filter(ValidationIssue.document_id == document_id)
        if is_resolved is not None:
            query = query.filter(ValidationIssue.is_resolved == is_resolved)

        search_term = q or search
        if search_term and search_term.strip():
            st = f"%{search_term.strip()}%"
            query = query.filter(
                or_(
                    ValidationIssue.description.ilike(st),
                    ValidationIssue.issue_type.ilike(st),
                    ValidationIssue.subsidiary.ilike(st),
                    ValidationIssue.mine.ilike(st),
                    ValidationIssue.metric_code.ilike(st),
                )
            )

        total = query.count()
        offset = (page - 1) * page_size
        items = query.order_by(
            desc(
                case(
                    (ValidationIssue.severity == "CRITICAL", 4),
                    (ValidationIssue.severity == "HIGH", 3),
                    (ValidationIssue.severity == "MEDIUM", 2),
                    else_=1,
                )
            ),
            desc(ValidationIssue.created_at),
        ).offset(offset).limit(page_size).all()

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [_issue_to_dict(i) for i in items],
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch data quality issues: {str(exc)}",
        )


@router.get("/issues/{issue_id}")
def get_issue(issue_id: str, db: Session = Depends(get_db)):
    """Retrieve a single data-quality issue by ID."""
    issue = db.query(ValidationIssue).filter(ValidationIssue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    return _issue_to_dict(issue)


@router.get("/stats")
def get_quality_stats(db: Session = Depends(get_db)):
    """
    Aggregate statistics for the Data Quality dashboard.
    Returns counts by severity, status, and issue type.
    """
    try:
        total = db.query(func.count(ValidationIssue.id)).scalar() or 0
        open_count = db.query(func.count(ValidationIssue.id)).filter(
            ValidationIssue.is_resolved == False
        ).scalar() or 0
        resolved_count = db.query(func.count(ValidationIssue.id)).filter(
            ValidationIssue.is_resolved == True
        ).scalar() or 0
        critical_count = db.query(func.count(ValidationIssue.id)).filter(
            ValidationIssue.severity == "CRITICAL",
            ValidationIssue.is_resolved == False,
        ).scalar() or 0
        high_count = db.query(func.count(ValidationIssue.id)).filter(
            ValidationIssue.severity == "HIGH",
            ValidationIssue.is_resolved == False,
        ).scalar() or 0

        # By issue type (top 10)
        by_type_rows = (
            db.query(ValidationIssue.issue_type, func.count(ValidationIssue.id).label("cnt"))
            .filter(ValidationIssue.is_resolved == False)
            .group_by(ValidationIssue.issue_type)
            .order_by(desc("cnt"))
            .limit(10)
            .all()
        )
        by_type = [{"issue_type": r.issue_type, "count": r.cnt} for r in by_type_rows]

        # By subsidiary (top 10)
        by_subsidiary_rows = (
            db.query(ValidationIssue.subsidiary, func.count(ValidationIssue.id).label("cnt"))
            .filter(ValidationIssue.is_resolved == False, ValidationIssue.subsidiary.isnot(None))
            .group_by(ValidationIssue.subsidiary)
            .order_by(desc("cnt"))
            .limit(10)
            .all()
        )
        by_subsidiary = [{"subsidiary": r.subsidiary, "count": r.cnt} for r in by_subsidiary_rows]

        # Conflicts
        total_conflicts = db.query(func.count(EvidenceConflict.id)).scalar() or 0
        open_conflicts = db.query(func.count(EvidenceConflict.id)).filter(
            EvidenceConflict.status == "OPEN"
        ).scalar() or 0

        return {
            "total_issues": total,
            "open_issues": open_count,
            "resolved_issues": resolved_count,
            "critical_open": critical_count,
            "high_open": high_count,
            "total_conflicts": total_conflicts,
            "open_conflicts": open_conflicts,
            "by_type": by_type,
            "by_subsidiary": by_subsidiary,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch data quality stats: {str(exc)}",
        )


# ── write endpoints (Reviewer / Admin only) ───────────────────────────────────

@router.post("/issues/{issue_id}/assign")
def assign_issue(
    issue_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_reviewer),
):
    """
    Assign a validation issue to an analyst/reviewer.
    Body: { "assignee": "username" }
    """
    actor = current_user["username"]
    issue = db.query(ValidationIssue).filter(ValidationIssue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    assignee = payload.get("assignee", "").strip()
    if not assignee:
        raise HTTPException(status_code=422, detail="assignee is required")

    issue.assigned_to = assignee
    issue.status = "ASSIGNED"
    db.commit()
    return {"message": f"Issue {issue_id} assigned to {assignee} by {actor}", "issue_id": issue_id}


@router.post("/issues/{issue_id}/resolve")
def resolve_issue(
    issue_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_reviewer),
):
    """
    Mark a validation issue as resolved.
    Body: { "notes": "optional resolution notes" }
    Requires Reviewer or Admin role.
    """
    actor = current_user["username"]
    issue = db.query(ValidationIssue).filter(ValidationIssue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    if issue.is_resolved:
        raise HTTPException(status_code=409, detail="Issue is already resolved")

    issue.is_resolved = True
    issue.status = "RESOLVED"
    issue.resolved_by = actor
    issue.resolved_at = datetime.now(timezone.utc)
    notes = payload.get("notes", "").strip()
    if notes:
        issue.reviewer_comments = notes
    db.commit()
    return {
        "message": f"Issue {issue_id} resolved by {actor}",
        "issue_id": issue_id,
        "resolved_by": actor,
    }


@router.post("/issues/{issue_id}/dismiss")
def dismiss_issue(
    issue_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_reviewer),
):
    """
    Dismiss a false-positive validation issue.
    Body: { "reason": "false positive note" }
    """
    actor = current_user["username"]
    issue = db.query(ValidationIssue).filter(ValidationIssue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    issue.status = "SUPERSEDED"
    issue.is_resolved = True
    issue.resolved_by = actor
    issue.resolved_at = datetime.now(timezone.utc)
    reason = payload.get("reason", "Dismissed as false positive").strip()
    issue.reviewer_comments = reason
    db.commit()
    return {"message": f"Issue {issue_id} dismissed by {actor}", "issue_id": issue_id}


# ── conflicts sub-resource ────────────────────────────────────────────────────

@router.get("/conflicts")
def list_conflicts(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
):
    """List EvidenceConflicts (cross-document contradictions)."""
    try:
        q = db.query(EvidenceConflict)
        if status_filter and status_filter != "ALL":
            q = q.filter(EvidenceConflict.status == status_filter)

        total = q.count()
        items = q.order_by(desc(EvidenceConflict.created_at)).offset(
            (page - 1) * page_size
        ).limit(page_size).all()

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [
                {
                    "id": c.id,
                    "metric_code": c.metric_code,
                    "primary_fact_id": c.primary_fact_id,
                    "conflicting_fact_id": c.conflicting_fact_id,
                    "description": c.description,
                    "discrepancy_percent": c.discrepancy_percent,
                    "status": c.status,
                    "resolution_notes": c.resolution_notes,
                    "resolved_by": c.resolved_by,
                    "resolved_at": _format_dt(c.resolved_at),
                    "created_at": _format_dt(c.created_at),
                }
                for c in items
            ],
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch conflicts: {str(exc)}",
        )
