from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.models.audit import AuditEvent
from app.schemas.audit import AuditEventResponse, AuditEventListResponse

router = APIRouter(prefix="/audit", tags=["Audit Trail"])


@router.get("", response_model=AuditEventListResponse)
def list_audit_events(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    action: Optional[str] = None,
    entity_type: Optional[str] = None
):
    """
    Returns immutable audit trail entries ordered by most recent first.
    Tracks all document uploads, deletions, verifications, and system modifications.
    """
    query = db.query(AuditEvent)

    if action:
        query = query.filter(AuditEvent.action == action)

    if entity_type:
        query = query.filter(AuditEvent.entity_type == entity_type)

    total = query.count()
    offset = (page - 1) * page_size
    items = query.order_by(desc(AuditEvent.timestamp)).offset(offset).limit(page_size).all()

    return AuditEventListResponse(
        items=[AuditEventResponse.model_validate(item) for item in items],
        total=total
    )
