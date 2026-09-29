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
    Durable persistent processing job tracking async multi-stage pipeline execution,
    retries, operator-safe error details, and idempotency.
    """
    __tablename__ = "processing_jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    stage = Column(String(50), nullable=False, default="QUEUED")  # QUEUED, CLASSIFYING, EXTRACTING, OCR, TABLE_PROCESSING, FACT_EXTRACTION, NORMALIZING, VALIDATING, INDEXING, READY, REVIEW_REQUIRED, FAILED
    status = Column(String(50), nullable=False, default="QUEUED")  # QUEUED, PROCESSING, REVIEW_REQUIRED, COMPLETED, FAILED
    progress = Column(Integer, default=0, nullable=False)
    message = Column(String(255), nullable=True)
    error_details = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    idempotency_key = Column(String(64), nullable=True, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    document = relationship("Document", back_populates="processing_jobs")

