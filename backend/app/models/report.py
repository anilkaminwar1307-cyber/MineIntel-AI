from sqlalchemy import Column, String, Integer, DateTime, Text
from app.core.database import Base
from app.models.base import generate_uuid, _utcnow


class GeneratedReport(Base):
    """
    Metadata and tracking for reports generated in Report Studio.
    """
    __tablename__ = "generated_reports"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False)
    report_type = Column(String(100), nullable=False)  # Production Summary, Parliamentary Brief, etc.
    parameters = Column(Text, nullable=True)          # JSON string of filter parameters
    status = Column(String(50), nullable=False, default="NOT_READY") # NOT_READY, PENDING, GENERATING, READY, FAILED
    pdf_status = Column(String(50), nullable=False, default="READY")  # READY, GENERATING, FAILED
    summary = Column(Text, nullable=True)
    content_json = Column(Text, nullable=True)
    output_path = Column(String(500), nullable=True)
    pdf_path = Column(String(500), nullable=True)
    pdf_filename = Column(String(255), nullable=True)
    pdf_size = Column(Integer, default=0)
    pdf_generated_at = Column(DateTime, nullable=True)
    evidence_count = Column(Integer, default=0)
    generated_by = Column(String(100), default="CMPDI Analyst")
    created_at = Column(DateTime, default=_utcnow, nullable=False)

