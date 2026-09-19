from sqlalchemy import Column, String, DateTime, Text
from app.core.database import Base
from app.models.base import generate_uuid, _utcnow
from app.models.enums import AuditAction


class AuditEvent(Base):
    """
    Immutable audit log entry recording all system mutations, uploads, approvals, and queries.
    """
    __tablename__ = "audit_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    timestamp = Column(DateTime, default=_utcnow, nullable=False, index=True)
    user = Column(String(100), nullable=False, default="CMPDI Analyst")
    action = Column(String(50), nullable=False, index=True)  # From AuditAction enum
    entity_type = Column(String(50), nullable=False, index=True)  # DOCUMENT, FACT, VALIDATION, REPORT, etc.
    entity_id = Column(String(36), nullable=True, index=True)
    details = Column(Text, nullable=True)
