"""
EvidenceChain 2.0 — Claim & ClaimEvidenceLink Models.

Adheres strictly to Rule 1 & Rule 2:
- Connects factual claims and narrative assertions in queries and reports directly to
  deterministic SQL calculations and grounded ExtractedFact provenance rows.
- Unsupported statements are flagged with UNSUPPORTED status.
"""
from sqlalchemy import Column, String, Float, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import generate_uuid, _utcnow
from app.models.enums import ClaimType, ClaimSupportStatus


class Claim(Base):
    """
    Represents an atomic numerical or narrative claim made in an Ask MineIntel answer,
    generated report, or executive brief.
    """
    __tablename__ = "claims"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    claim_type = Column(String(50), nullable=False, default=ClaimType.EVIDENCE_FACT.value)
    text = Column(Text, nullable=False)
    query_id = Column(String(36), nullable=True, index=True)
    report_id = Column(String(36), nullable=True, index=True)
    support_status = Column(String(50), nullable=False, default=ClaimSupportStatus.SUPPORTED.value)
    confidence = Column(Float, nullable=False, default=1.0)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    # Relationships
    evidence_links = relationship(
        "ClaimEvidenceLink",
        back_populates="claim",
        cascade="all, delete-orphan"
    )


class ClaimEvidenceLink(Base):
    """
    Links a Claim to either an ExtractedFact or a CalculationRun (or both).
    Provides bidirectional inspectability in the universal EvidenceDrawer.
    """
    __tablename__ = "claim_evidence_links"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    claim_id = Column(String(36), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False, index=True)
    fact_id = Column(String(36), nullable=True, index=True)           # Soft ref to extracted_facts
    calculation_id = Column(String(36), nullable=True, index=True)    # Soft ref to calculation_runs
    relationship_type = Column(String(50), nullable=False, default="DIRECT_EVIDENCE")  # DIRECT_EVIDENCE, CALCULATION_INPUT, CONTEXTUAL
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    claim = relationship("Claim", back_populates="evidence_links")
_claim_link_calc_idx = Index("ix_claim_links_calc_id", ClaimEvidenceLink.calculation_id)
