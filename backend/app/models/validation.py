from sqlalchemy import Column, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import generate_uuid, _utcnow


class ValidationIssue(Base):
    """
    Validation issues flagged by ReportGuard or automated validation rules.
    """
    __tablename__ = "validation_issues"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    fact_id = Column(String(36), ForeignKey("extracted_facts.id", ondelete="CASCADE"), nullable=True, index=True)
    
    issue_type = Column(String(100), nullable=False)  # MISSING_UNIT, OUTLIER_VALUE, UNRESOLVED_CONFLICT, etc.
    severity = Column(String(20), nullable=False, default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    description = Column(Text, nullable=False)
    is_resolved = Column(Boolean, default=False, nullable=False)
    resolved_by = Column(String(100), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="validation_issues")
    fact = relationship("ExtractedFact", back_populates="validation_issues")


class EvidenceConflict(Base):
    """
    Cross-document or temporal contradictions between facts identified by NumberSafe AI.
    """
    __tablename__ = "evidence_conflicts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    metric_code = Column(String(100), nullable=False, index=True)
    primary_fact_id = Column(String(36), nullable=False, index=True)
    conflicting_fact_id = Column(String(36), nullable=False, index=True)
    description = Column(Text, nullable=False)
    discrepancy_percent = Column(Float, nullable=True)
    status = Column(String(50), default="OPEN", nullable=False)  # OPEN, RESOLVED, DISMISSED
    resolution_notes = Column(Text, nullable=True)
    resolved_by = Column(String(100), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
