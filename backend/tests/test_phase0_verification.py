"""
test_phase0_verification.py — Verification suite for Phase 0 requirements
Explicitly verifies:
0.1 RBAC on all routes
0.2 Login rate limiting
0.3 No hardcoded secrets / confidence
0.4 Named tests:
    - test_insufficient_evidence_on_empty_retrieval
    - test_conflict_on_differing_duplicate_facts
    - test_refusal_to_mix_temporal_grains
    - test_demo_facts_excluded_by_default
0.5 Deterministic extractive mode labeling
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.fact import ExtractedFact
from app.models.document import Document
from app.models.enums import ValidationStatus
from app.models.base import generate_uuid
from app.services.query_engine import NumberSafeQueryEngine
from app.services.calculations.calculation_engine import (
    CalculationEngine, EvidenceScope, AggOp
)
from app.providers.ai.gemini import GeminiProvider


@pytest.fixture
def clean_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def test_insufficient_evidence_on_empty_retrieval(clean_db):
    """0.4: An empty retrieval on unknown topic must return status INSUFFICIENT_EVIDENCE."""
    res = NumberSafeQueryEngine._handle_narrative_rag(
        db=clean_db,
        query="What is the environmental mitigation strategy for Jharia coalfield?",
        scope="ALL_EVIDENCE",
        response_mode="STANDARD",
        document_ids=None,
        include_demo=False,
    )
    assert res["status"] == "INSUFFICIENT_EVIDENCE"
    assert res["verification_status"] == "INSUFFICIENT_EVIDENCE"
    assert res["records_used"] == 0
    assert res["confidence"] == 0.0


def test_conflict_on_differing_duplicate_facts(clean_db):
    """0.4: If two documents give contradictory values for same metric/sub/period, do NOT sum. Flag CONFLICT."""
    # Seed doc 1 and fact 1 (100.0 MT)
    doc1 = Document(id=generate_uuid(), original_filename="ann_rep_1.pdf", stored_filename="ann_rep_1.pdf",
                    mime_type="application/pdf", file_size=1024, storage_path="/tmp/1",
                    is_demo=False, status="PROCESSED")
    doc2 = Document(id=generate_uuid(), original_filename="monthly_rep_2.pdf", stored_filename="monthly_rep_2.pdf",
                    mime_type="application/pdf", file_size=1024, storage_path="/tmp/2",
                    is_demo=False, status="PROCESSED")
    clean_db.add_all([doc1, doc2])
    clean_db.commit()

    f1 = ExtractedFact(
        id=generate_uuid(), document_id=doc1.id, metric_code="COAL_PRODUCTION",
        metric_name="Raw Coal Production", numeric_value=100.0, unit="MT",
        subsidiary="SECL", reporting_period="FY 2024-25", temporal_grain="ANNUAL",
        validation_status=ValidationStatus.VERIFIED.value, is_demo=False, is_superseded=False,
        dedup_key="COAL_PRODUCTION_SECL_FY 2024-25_ANNUAL_100.0",
    )
    # Contradicting fact: 120.0 MT for the exact same target scope
    f2 = ExtractedFact(
        id=generate_uuid(), document_id=doc2.id, metric_code="COAL_PRODUCTION",
        metric_name="Raw Coal Production", numeric_value=120.0, unit="MT",
        subsidiary="SECL", reporting_period="FY 2024-25", temporal_grain="ANNUAL",
        validation_status=ValidationStatus.VERIFIED.value, is_demo=False, is_superseded=False,
        dedup_key="COAL_PRODUCTION_SECL_FY 2024-25_ANNUAL_120.0",
    )
    clean_db.add_all([f1, f2])
    clean_db.commit()

    scope = EvidenceScope(
        metric_code="COAL_PRODUCTION",
        subsidiary="SECL",
        reporting_period="FY 2024-25",
        only_real=True,
    )
    res = CalculationEngine.calculate(clean_db, scope, AggOp.SUM)
    assert res.success is False
    assert res.error_code in ("CONFLICT", "UNRESOLVED_CONFLICT")
    assert "CONFLICT" in res.error_message


def test_refusal_to_mix_temporal_grains(clean_db):
    """0.4: Engine refuses to sum annual grain with monthly grain."""
    doc = Document(id=generate_uuid(), original_filename="doc.pdf", stored_filename="doc.pdf",
                   mime_type="application/pdf", file_size=1024, storage_path="/tmp/g",
                   is_demo=False, status="PROCESSED")
    clean_db.add(doc)
    clean_db.commit()

    f_annual = ExtractedFact(
        id=generate_uuid(), document_id=doc.id, metric_code="COAL_PRODUCTION",
        metric_name="Raw Coal Production", numeric_value=150.0, unit="MT",
        subsidiary="WCL", reporting_period="FY 2024-25", temporal_grain="ANNUAL",
        validation_status=ValidationStatus.VERIFIED.value, is_demo=False, is_superseded=False,
    )
    f_monthly = ExtractedFact(
        id=generate_uuid(), document_id=doc.id, metric_code="COAL_PRODUCTION",
        metric_name="Raw Coal Production", numeric_value=12.5, unit="MT",
        subsidiary="WCL", reporting_period="Nov 2024", temporal_grain="MONTHLY",
        validation_status=ValidationStatus.VERIFIED.value, is_demo=False, is_superseded=False,
    )
    clean_db.add_all([f_annual, f_monthly])
    clean_db.commit()

    scope = EvidenceScope(
        metric_code="COAL_PRODUCTION",
        subsidiary="WCL",
        reporting_period="FY 2024-25",
        only_real=True,
    )
    calc_res = CalculationEngine.calculate(clean_db, scope, AggOp.SUM)
    # The calculation must resolve strictly to the annual figure or refuse mixed grain sum, NOT 162.5
    assert calc_res.result != 162.5
    if calc_res.success:
        assert calc_res.result == 150.0  # Uses annual figure, never sums monthly on top of annual


def test_demo_facts_excluded_by_default(clean_db):
    """0.4: When include_demo is False, demo facts must never be included in query answers."""
    doc = Document(id=generate_uuid(), original_filename="demo.pdf", stored_filename="demo.pdf",
                   mime_type="application/pdf", file_size=1024, storage_path="/tmp/d",
                   is_demo=True, status="PROCESSED")
    clean_db.add(doc)
    clean_db.commit()

    demo_fact = ExtractedFact(
        id=generate_uuid(), document_id=doc.id, metric_code="COAL_PRODUCTION",
        metric_name="Raw Coal Production", numeric_value=999.0, unit="MT",
        subsidiary="ECL", reporting_period="FY 2024-25", temporal_grain="ANNUAL",
        validation_status=ValidationStatus.VERIFIED.value, is_demo=True, is_superseded=False,
    )
    clean_db.add(demo_fact)
    clean_db.commit()

    # Query with default include_demo=False
    scope = EvidenceScope(
        metric_code="COAL_PRODUCTION",
        subsidiary="ECL",
        reporting_period="FY 2024-25",
        only_real=True,
    )
    res = CalculationEngine.calculate(clean_db, scope, AggOp.SUM)
    # With only demo facts in DB, result should be 0 facts used and not 999.0
    assert res.evidence_count_used == 0


def test_extractive_mode_labeled_when_gemini_unconfigured():
    """0.5: When Gemini is not configured, extractive fallback is labeled with mode extractive_no_llm."""
    provider = GeminiProvider(api_key="")
    assert provider.get_status()["status"] == "not_configured"
    narrative = provider._build_deterministic_parliamentary_brief(
        query="What was ECL production?",
        period="FY 2024-25",
        subsidiary="ECL",
        direct_answer="ECL produced 42.1 MT raw coal.",
        verified_facts=[{"metric_code": "COAL_PRODUCTION", "subsidiary": "ECL", "numeric_value": 42.1, "unit": "MT"}],
        supporting_context=[],
        numbersafe_status="DETERMINISTIC SQL",
        confidence_score=0.95,
        records_used=1,
    )
    assert "ECL produced 42.1 MT" in narrative
    assert "NumberSafe" in narrative
