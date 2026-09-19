"""
Phase 2 Models: Document processing artifacts.
Stores per-page, per-sheet, per-table, and quality data for each processed document.
"""
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import generate_uuid, _utcnow


class DocumentPage(Base):
    """
    Stores extracted text and metadata for each PDF page.
    """
    __tablename__ = "document_pages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)

    page_number = Column(Integer, nullable=False)
    raw_text = Column(Text, nullable=True)              # Native PDF text or OCR output
    char_count = Column(Integer, default=0)
    word_count = Column(Integer, default=0)
    has_native_text = Column(Boolean, default=True)    # False = scanned / image page
    is_ocr_page = Column(Boolean, default=False)
    ocr_confidence = Column(Float, nullable=True)      # 0.0-1.0 if OCR was applied
    extraction_method = Column(String(50), default="PDF_NATIVE")  # PDF_NATIVE, OCR_TESSERACT, OCR_PADDLE

    created_at = Column(DateTime, default=_utcnow, nullable=False)

    document = relationship("Document", back_populates="pages")


class DocumentSheet(Base):
    """
    Stores Excel worksheet metadata and preview data.
    """
    __tablename__ = "document_sheets"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)

    sheet_name = Column(String(200), nullable=False)
    sheet_index = Column(Integer, nullable=False, default=0)
    row_count = Column(Integer, default=0)
    col_count = Column(Integer, default=0)
    used_range = Column(String(50), nullable=True)     # e.g. "A1:J42"
    header_row = Column(Integer, nullable=True)        # Detected header row index (1-based)
    has_merged_cells = Column(Boolean, default=False)
    preview_json = Column(Text, nullable=True)         # First 10 rows as JSON string

    created_at = Column(DateTime, default=_utcnow, nullable=False)

    document = relationship("Document", back_populates="sheets")
    tables = relationship("DocumentTable", back_populates="sheet", cascade="all, delete-orphan",
                          foreign_keys="DocumentTable.sheet_id")


class DocumentTable(Base):
    """
    Represents a detected table within a PDF page or Excel sheet.
    """
    __tablename__ = "document_tables"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    sheet_id = Column(String(36), ForeignKey("document_sheets.id", ondelete="CASCADE"), nullable=True)

    table_index = Column(Integer, nullable=False, default=0)
    source_type = Column(String(20), nullable=False)   # PDF, EXCEL, CSV, OCR
    page_number = Column(Integer, nullable=True)       # For PDF tables
    sheet_name = Column(String(200), nullable=True)    # For Excel tables
    title = Column(String(500), nullable=True)         # Detected or inferred table title
    source_range = Column(String(100), nullable=True)  # e.g. "A3:F18" or "Page 4, Table 2"
    row_count = Column(Integer, default=0)
    col_count = Column(Integer, default=0)
    headers_json = Column(Text, nullable=True)         # JSON list of header names
    data_json = Column(Text, nullable=True)            # JSON list-of-lists of cell values
    confidence = Column(Float, default=1.0)            # Table structure confidence
    structure_status = Column(String(50), default="CLEAN")  # CLEAN, TABLE_STRUCTURE_UNCERTAIN

    created_at = Column(DateTime, default=_utcnow, nullable=False)

    document = relationship("Document", back_populates="tables")
    sheet = relationship("DocumentSheet", back_populates="tables", foreign_keys=[sheet_id])


class DocumentQuality(Base):
    """
    Quality assessment and enhancement metadata for scanned documents and images.
    """
    __tablename__ = "document_quality"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True, unique=True)

    # Overall quality profile
    quality_score = Column(Float, nullable=True)                    # 0.0-1.0 composite
    quality_label = Column(String(30), nullable=True)              # GOOD, FAIR, POOR, UNUSABLE
    enhancement_recommended = Column(Boolean, default=False)
    enhancement_applied = Column(Boolean, default=False)
    enhancement_methods = Column(Text, nullable=True)              # Comma-separated list

    # Per-dimension assessments
    blur_level = Column(String(20), nullable=True)                 # low, medium, high
    contrast_level = Column(String(20), nullable=True)             # low, medium, high
    noise_level = Column(String(20), nullable=True)                # low, medium, high
    skew_angle = Column(Float, nullable=True)                      # Detected skew in degrees
    detected_dpi = Column(Integer, nullable=True)
    orientation_correction = Column(Integer, nullable=True)        # 0, 90, 180, 270 degrees

    # Before/after comparison
    quality_score_before = Column(Float, nullable=True)
    quality_score_after = Column(Float, nullable=True)
    ocr_confidence_before = Column(Float, nullable=True)
    ocr_confidence_after = Column(Float, nullable=True)

    # Source tracking
    original_path = Column(String(500), nullable=True)
    enhanced_path = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=_utcnow, nullable=False)

    document = relationship("Document", back_populates="quality")


class ProcessingLog(Base):
    """
    Timestamped pipeline log entries for each document processing run.
    """
    __tablename__ = "processing_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)

    level = Column(String(10), nullable=False, default="INFO")    # INFO, WARNING, ERROR
    stage = Column(String(50), nullable=True)
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=_utcnow, nullable=False)

    document = relationship("Document", back_populates="processing_logs")
