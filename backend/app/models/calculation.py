"""
NumberSafe 2.0 — CalculationRun & CalculationInput ORM Models

Every numeric result produced by CalculationEngine is persisted here
so that every displayed answer is reproducible and auditable.

calculation_runs  — one row per computation (e.g. SECL production FY2024-25)
calculation_inputs — one row per fact included or excluded in that computation
"""
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import generate_uuid, _utcnow


class CalculationRun(Base):
    """Records metadata for each deterministic calculation performed."""
    __tablename__ = "calculation_runs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    operation = Column(String(50), nullable=False)           # SUM / LATEST / WAVG / RATIO
    metric_code = Column(String(100), nullable=False, index=True)
    filters_json = Column(Text, nullable=True)               # JSON dump of EvidenceScope
    result = Column(Float, nullable=True)                    # None if error
    unit = Column(String(50), nullable=True)
    formula = Column(Text, nullable=True)
    calculation_method = Column(String(100), nullable=True)
    sql_description = Column(Text, nullable=True)
    success = Column(Boolean, nullable=False, default=False)
    error_code = Column(String(100), nullable=True)

    # Evidence statistics
    evidence_count = Column(Integer, nullable=False, default=0)
    evidence_used_count = Column(Integer, nullable=False, default=0)
    verified_count = Column(Integer, nullable=False, default=0)
    excluded_count = Column(Integer, nullable=False, default=0)
    verified_pct = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)

    # Scope metadata
    warnings_json = Column(Text, nullable=True)              # JSON list of warning strings
    is_demo_scope = Column(String(30), nullable=True)        # REAL / DEMO / MIXED
    initiated_by = Column(String(100), nullable=True)        # system / analyst name

    created_at = Column(DateTime, default=_utcnow, nullable=False)

    # Relationship
    inputs = relationship(
        "CalculationInput",
        back_populates="run",
        cascade="all, delete-orphan",
    )


class CalculationInput(Base):
    """Records which facts were included in or excluded from a calculation."""
    __tablename__ = "calculation_inputs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    calculation_id = Column(
        String(36),
        ForeignKey("calculation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fact_id = Column(String(36), nullable=False, index=True)   # FK to extracted_facts (soft ref)
    inclusion_status = Column(String(20), nullable=False)       # INCLUDED / EXCLUDED
    exclusion_reason = Column(Text, nullable=True)              # human-readable reason string
    weight = Column(Float, nullable=True)                       # for weighted-average ops

    run = relationship("CalculationRun", back_populates="inputs")


# ─── Indexes ─────────────────────────────────────────────────────────────────
_calc_runs_metric_idx = Index(
    "ix_calc_runs_metric_code",
    CalculationRun.metric_code,
)
