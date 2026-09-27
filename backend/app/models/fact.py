from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import generate_uuid, _utcnow
from app.models.enums import ValidationStatus, ExtractionMethod


class ExtractedFact(Base):
    """
    Core model for NumberSafe AI and EvidenceChain.
    Stores every individual extracted numerical or qualitative mining fact
    with granular provenance coordinates back to page, sheet, row, cell, table.
    """
    __tablename__ = "extracted_facts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Normalized and raw metric identification
    metric_code = Column(String(100), nullable=False, index=True)  # e.g. COAL_PROD_RAW, OVERBURDEN_OB
    metric_name = Column(String(200), nullable=False)               # Human-readable canonical name
    raw_metric_name = Column(String(255), nullable=True)            # Original text in document
    
    # Values: NumberSafe prioritizes numeric_value for all quantitative operations
    numeric_value = Column(Float, nullable=True, index=True)
    text_value = Column(String(500), nullable=True)
    unit = Column(String(50), nullable=True)                        # Canonical unit: MT, BCM, Meters
    raw_unit = Column(String(50), nullable=True)                    # Unit as written in doc
    
    # Mining domain entity hierarchy (MineGraph coordinates)
    reporting_period = Column(String(50), nullable=True, index=True) # e.g. "2024-Q3", "FY 2023-24"
    organization = Column(String(100), nullable=False, default="Coal India Limited")
    subsidiary = Column(String(50), nullable=True, index=True)      # ECL, BCCL, CCL, NCL, WCL, SECL, MCL, CMPDI
    coalfield = Column(String(100), nullable=True, index=True)      # Jharia, Raniganj, Singrauli, Korba
    mine = Column(String(100), nullable=True, index=True)
    location = Column(String(255), nullable=True)
    
    # EvidenceChain Granular Provenance (Source Tracking)
    page_number = Column(Integer, nullable=True)                    # For PDF / Reports
    sheet_name = Column(String(100), nullable=True)                 # For Excel Workbooks
    row_number = Column(Integer, nullable=True)                     # For Excel / CSV / Tables
    column_name = Column(String(100), nullable=True)                # For Excel / CSV / Tables
    cell_reference = Column(String(50), nullable=True)              # e.g. "D18"
    table_reference = Column(String(200), nullable=True)            # Table title or index
    source_context = Column(Text, nullable=True)                    # Raw surrounding text / OCR line snippet
    
    # Reliability, Confidence & Verification
    extraction_method = Column(String(50), nullable=False, default=ExtractionMethod.STRUCTURED_TABLE)
    confidence_score = Column(Float, nullable=False, default=1.0)   # 0.0 - 1.0
    validation_status = Column(String(50), nullable=False, default=ValidationStatus.EXTRACTED, index=True)
    human_verified = Column(Boolean, nullable=False, default=False)
    verified_by = Column(String(100), nullable=True)
    
    # Demo flag
    is_demo = Column(Boolean, default=False, nullable=False, index=True)

    # NumberSafe 2.0 — temporal grain of this observation
    # ANNUAL / QUARTERLY / MONTHLY / POINT_IN_TIME / CUMULATIVE_YTD
    # Used by duplicate_detector to prevent annual+monthly double-count
    temporal_grain = Column(String(30), nullable=True, index=True)

    # Prompt 2 — Source object tracking & Fact-level deduplication
    source_object_type = Column(String(50), nullable=True)  # TABLE, PAGE, SHEET, OCR_BLOCK
    source_object_id = Column(String(100), nullable=True)
    source_hash = Column(String(64), nullable=True)
    dedup_key = Column(String(255), nullable=True, index=True)

    # Prompt 3 — EvidenceChain 2.0: Original Extraction Preservation & Version Control
    original_numeric_value = Column(Float, nullable=True)
    original_metric_code = Column(String(100), nullable=True)
    original_unit = Column(String(50), nullable=True)
    superseded_by_id = Column(String(36), nullable=True, index=True)
    is_superseded = Column(Boolean, default=False, nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="facts")
    validation_issues = relationship("ValidationIssue", back_populates="fact", cascade="all, delete-orphan")


# Composite index for common analytics queries (subsidiary + metric + period)
_fact_analytics_index = Index(
    'ix_facts_sub_metric_period',
    ExtractedFact.subsidiary,
    ExtractedFact.metric_code,
    ExtractedFact.reporting_period
)
