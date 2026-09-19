from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from app.models.audit import AuditEvent
from app.models.enums import AuditAction
from app.core.logging import logger


def log_audit_event(
    db: Session,
    action: AuditAction,
    entity_type: str,
    entity_id: Optional[str] = None,
    user: str = "CMPDI Analyst",
    details: Optional[str] = None
) -> AuditEvent:
    """
    Creates an immutable audit log entry.
    """
    event = AuditEvent(
        timestamp=datetime.now(timezone.utc),
        user=user,
        action=action.value if hasattr(action, 'value') else str(action),
        entity_type=entity_type,
        entity_id=entity_id,
        details=details
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    logger.info(f"AUDIT: [{user}] {event.action} on {entity_type}:{entity_id or '-'} - {details or ''}")
    return event
