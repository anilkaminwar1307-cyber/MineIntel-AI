from sqlalchemy import Column, String, DateTime, Text
from app.core.database import Base
from app.models.base import generate_uuid, _utcnow


class QueryHistory(Base):
    """
    Log of queries submitted to Ask MineIntel, their response modes, and retrieved evidence.
    """
    __tablename__ = "query_history"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    query_text = Column(Text, nullable=False)
    scope = Column(String(50), nullable=False, default="ALL_EVIDENCE")  # CURRENT_DOCUMENT, SELECTED_DOCUMENTS, ALL_EVIDENCE
    response_mode = Column(String(50), nullable=False, default="STANDARD")  # STANDARD, OFFICIAL, PARLIAMENTARY
    answer_text = Column(Text, nullable=True)
    evidence_citations = Column(Text, nullable=True)  # JSON serialized list of fact citations
    user_name = Column(String(100), default="CMPDI Analyst")
    created_at = Column(DateTime, default=_utcnow, nullable=False)
