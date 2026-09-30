from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, Float, Boolean, Index
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import generate_uuid, _utcnow
from app.models.enums import DocumentStatus, FileType


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False, unique=True)
    file_type = Column(String(20), nullable=False, default=FileType.UNKNOWN)
    source_type = Column(String(30), nullable=True)     # digital_pdf, scanned_pdf, xlsx, csv, image, txt
    mime_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)  # in bytes

    # Metadata fields
    document_category = Column(String(100), nullable=True, default="General Mining Report")
    organization = Column(String(100), nullable=False, default="CMPDI / CIL")
    reporting_period = Column(String(50), nullable=True)
    storage_path = Column(String(500), nullable=False)

    # Content statistics
    page_count = Column(Integer, default=0)
    sheet_count = Column(Integer, default=0)
    table_count = Column(Integer, default=0)

    # Quality summary
    quality_label = Column(String(30), nullable=True)  # GOOD, FAIR, POOR
    average_confidence = Column(Float, nullable=True)

    # Lifecycle & status
    status = Column(String(50), nullable=False, default=DocumentStatus.UPLOADED)
    processing_progress = Column(Integer, default=0)  # 0 - 100%
    processing_message = Column(String(255), nullable=True)
    processing_error = Column(Text, nullable=True)

    # Fingerprinting & Versioning (Prompt 2)
    sha256 = Column(String(64), nullable=True, index=True)
    source_version = Column(String(50), default="v1.0", nullable=True)
    revision_number = Column(Integer, default=1, nullable=False)
    supersedes_document_id = Column(String(36), nullable=True, index=True)
    is_latest_version = Column(Boolean, default=True, nullable=False)
    revision_date = Column(DateTime, nullable=True)
    pipeline_version = Column(String(50), default="2.0", nullable=True)

    # Derived counters & tracking
    fact_count = Column(Integer, default=0)
    real_fact_count = Column(Integer, default=0)
    warning_count = Column(Integer, default=0)
    topic_count = Column(Integer, default=0)

    # Demo / synthetic data flag (set by seed_large.py)
    is_demo = Column(Boolean, default=False, nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    processing_started_at = Column(DateTime, nullable=True)
    processing_completed_at = Column(DateTime, nullable=True)

    # Relationships
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    facts = relationship("ExtractedFact", back_populates="document", cascade="all, delete-orphan")
    validation_issues = relationship("ValidationIssue", back_populates="document", cascade="all, delete-orphan")
    processing_jobs = relationship("ProcessingJob", back_populates="document", cascade="all, delete-orphan")
    pages = relationship("DocumentPage", back_populates="document", cascade="all, delete-orphan")
    sheets = relationship("DocumentSheet", back_populates="document", cascade="all, delete-orphan")
    tables = relationship("DocumentTable", back_populates="document", cascade="all, delete-orphan")
    quality = relationship("DocumentQuality", back_populates="document", cascade="all, delete-orphan", uselist=False)
    processing_logs = relationship("ProcessingLog", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    page_number = Column(Integer, nullable=True)
    sheet_name = Column(String(100), nullable=True)
    section = Column(String(200), nullable=True)        # Heading/section detected
    content = Column(Text, nullable=False)
    token_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="chunks")
