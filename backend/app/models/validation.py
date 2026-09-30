from sqlalchemy import Column, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import generate_uuid, _utcnow


class ValidationIssue(Base):
    """
    Data Quality & Validation issues flagged by the DataQuality engine or automated rules.
    """
    __tablename__ = "validation_issues"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    fact_id = Column(String(36), ForeignKey("extracted_facts.id", ondelete="CASCADE"), nullable=True, index=True)
    
    issue_type = Column(String(100), nullable=False, index=True)
    severity = Column(String(20), nullable=False, default="MEDIUM", index=True)  # LOW, MEDIUM, HIGH, CRITICAL
    description = Column(Text, nullable=False)
    
    status = Column(String(50), default="OPEN", nullable=False, index=True)  # OPEN, ASSIGNED, UNDER_REVIEW, APPROVED, REJECTED, RESOLVED, SUPERSEDED
    assigned_to = Column(String(100), nullable=True)
    
    # Mining coordinates for localized quality filtering
    mine = Column(String(100), nullable=True, index=True)
    subsidiary = Column(String(50), nullable=True, index=True)
    reporting_period = Column(String(50), nullable=True, index=True)
    metric_code = Column(String(100), nullable=True, index=True)

    # Review & value proposition
    previous_value = Column(Float, nullable=True)
    proposed_value = Column(Float, nullable=True)
    previous_unit = Column(String(50), nullable=True)
    proposed_unit = Column(String(50), nullable=True)
    reviewer_comments = Column(Text, nullable=True)
    evidence_context = Column(Text, nullable=True)

    is_resolved = Column(Boolean, default=False, nullable=False, index=True)
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
