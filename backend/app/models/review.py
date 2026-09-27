from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import generate_uuid, _utcnow


class ReviewAction(Base):
    """
    Human-in-the-loop review actions taken on facts, conflicts, or document validations.
    Preserves immutable before/after state deltas.
    """
    __tablename__ = "review_actions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), nullable=True, index=True)
    fact_id = Column(String(36), nullable=True, index=True)
    conflict_id = Column(String(36), nullable=True, index=True)
    reviewer_name = Column(String(100), nullable=False, default="CMPDI Analyst")
    action = Column(String(50), nullable=False)  # APPROVED, MODIFIED, REJECTED, ESCALATED, CONFLICT_RESOLVED, SUPERSEDED
    previous_value = Column(String(255), nullable=True)
    new_value = Column(String(255), nullable=True)
    previous_metric = Column(String(100), nullable=True)
    new_metric = Column(String(100), nullable=True)
    previous_unit = Column(String(50), nullable=True)
    new_unit = Column(String(50), nullable=True)
    previous_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)


class ProcessingJob(Base):
    """
    Tracks async or multi-stage document processing pipeline steps.
    """
    __tablename__ = "processing_jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    stage = Column(String(50), nullable=False)  # CLASSIFYING, EXTRACTING, OCR, VALIDATING, etc.
    status = Column(String(50), nullable=False, default="PENDING")  # PENDING, RUNNING, COMPLETED, FAILED
    progress = Column(Integer, default=0)
    message = Column(String(255), nullable=True)
    error_details = Column(Text, nullable=True)
    started_at = Column(DateTime, default=_utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    document = relationship("Document", back_populates="processing_jobs")

