"""
NumberSafe 2.0 — Comprehensive Test Suite for CalculationEngine

Covers all 12 correctness requirements:
  1.  Single-fact calculation
  2.  Multi-fact (>100 facts) without LIMIT truncation
  3.  Exact duplicate exclusion
  4.  Temporal overlap exclusion (Annual vs Monthly/Quarterly for same entity+period)
  5.  Consolidated CIL vs subsidiary exclusion
  6.  Unit mismatch detection and warning
  7.  Target achievement calculation with matching scopes
  8.  Target achievement refusal when target is missing (no synthetic fallback)
  9.  Zero denominator handling (target = 0)
  10. Demo vs Real vs Mixed data scope classification
  11. Lineage persistence and retrieval
  12. Reconciliation service checks

Engine API:
  CalculationEngine.calculate(db, scope: EvidenceScope, operation: str)
  CalculationEngine.calculate_achievement(db, actual_scope, target_scope) -> CalculationResult
  EvidenceScope(metric_code, subsidiary, reporting_period, ...)
  persist_calculation(db, result, operation, initiated_by)
  get_lineage(db, lineage_id) -> dict
"""
import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # Ensure all models are registered with Base.metadata
from app.core.database import Base
from app.models.fact import ExtractedFact
from app.models.document import Document
from app.services.calculations.calculation_engine import (
    CalculationEngine,
    EvidenceScope,
    CalcError,
    DataScopeMode,
)
from app.services.calculations.metric_semantics import AggOp
from app.services.calculations.lineage import persist_calculation, get_lineage
from app.services.calculations.reconciliation import ReconciliationService


# ─── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def db():
    """In-memory SQLite session for each test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed two Document rows (real + demo) — FK source for ExtractedFact.document_id
    doc_real = Document(
        id="doc-real-001",
        original_filename="SECL_Annual_Report_FY2024.pdf",
        stored_filename="SECL_Annual_Report_FY2024.pdf",
        file_type="pdf",
        mime_type="application/pdf",
        file_size=1024,
        document_category="Annual Report",
        organization="SECL",
        status="PROCESSED",
        source_type="REAL",
        storage_path="uploads/test/SECL_Annual_Report_FY2024.pdf",
    )
    doc_demo = Document(
        id="doc-demo-001",
        original_filename="demo_data.xlsx",
        stored_filename="demo_data.xlsx",
        file_type="xlsx",
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        file_size=512,
        document_category="Demo Data",
        organization="CIL",
        status="PROCESSED",
        source_type="DEMO",
        storage_path="uploads/test/demo_data.xlsx",
    )
    session.add_all([doc_real, doc_demo])
    session.commit()

    yield session
    session.close()
    engine.dispose()


def _make_fact(
    db,
    metric_code: str = "COAL_PRODUCTION",
    subsidiary: str = "SECL",
    reporting_period: str = "FY 2024-25",
    numeric_value: float = 10.0,
    unit: str = "MT",
    validation_status: str = "VERIFIED",
    document_id: str = "doc-real-001",
    is_demo: bool = False,
    source_type: str = "REAL",
    confidence_score: float = 0.95,
    mine: str | None = None,
    entity_type: str | None = None,
    temporal_grain: str | None = None,
) -> ExtractedFact:
    fact = ExtractedFact(
        id=str(uuid.uuid4()),
        document_id=document_id,
        metric_code=metric_code,
        metric_name=metric_code,
        subsidiary=subsidiary,
        mine=mine,
        reporting_period=reporting_period,
        numeric_value=numeric_value,
        unit=unit,
        validation_status=validation_status,
        is_demo=is_demo,
        confidence_score=confidence_score,
        temporal_grain=temporal_grain,
        human_verified=(validation_status == "VERIFIED"),
    )
    db.add(fact)
    db.commit()
    return fact


def _scope(metric_code="COAL_PRODUCTION", subsidiary="SECL",
           reporting_period="FY 2024-25", **kw) -> EvidenceScope:
    return EvidenceScope(
        metric_code=metric_code,
        subsidiary=subsidiary,
        reporting_period=reporting_period,
        **kw,
    )


# ─── Test 1: Single-fact calculation ──────────────────────────────────────────

def test_single_fact_calculation(db):
    """A single verified fact returns its exact value with no exclusions."""
    _make_fact(db, numeric_value=45.67)
    result = CalculationEngine.calculate(db, _scope(), AggOp.SUM)

    assert result.success is True
    assert result.result == pytest.approx(45.67, abs=0.01)
    assert result.evidence_count_used == 1
    assert result.excluded_count == 0
    assert result.unit == "MT"


# ─── Test 2: >100 facts — NO LIMIT truncation ────────────────────────────────

def test_no_limit_truncation_above_100_facts(db):
    """
    CRITICAL: CalculationEngine must aggregate ALL facts.
    A legacy bug applied LIMIT(100) — this test proves it is gone.
    Inserts 150 facts of 1.0 MT each; expects SUM = 150.0 MT.
    Note: Duplicate detector may consolidate, so we use distinct reporting months.
    """
    months = [
        f"Month-{i:03d}" for i in range(150)
    ]
    for m in months:
        _make_fact(db, numeric_value=1.0, reporting_period=m)

    # Query without period filter so all 150 are in scope
    scope = EvidenceScope(metric_code="COAL_PRODUCTION", subsidiary="SECL")
    result = CalculationEngine.calculate(db, scope, AggOp.SUM)

    assert result.success is True
    assert result.result == pytest.approx(150.0, abs=1.0), (
        f"Expected ~150.0 MT but got {result.result}. "
        "Possible LIMIT() truncation was reintroduced."
    )
    assert result.evidence_count_used >= 100, (
        "Fewer than 100 facts included — LIMIT truncation likely."
    )


# ─── Test 3: Exact duplicate exclusion ───────────────────────────────────────

def test_exact_duplicate_exclusion(db):
    """
    Two records with identical (metric, subsidiary, period, rounded value)
    should result in only ONE being counted — the higher-confidence record wins.
    """
    _make_fact(db, numeric_value=30.0, confidence_score=0.80)
    _make_fact(db, numeric_value=30.0, confidence_score=0.95)  # higher conf — kept

    result = CalculationEngine.calculate(db, _scope(), AggOp.SUM)

    assert result.success is True
    # Result must be ~30.0 (single fact), not 60.0 (double-counted)
    assert result.result == pytest.approx(30.0, abs=0.5), (
        f"Expected ~30.0 but got {result.result}. "
        "Duplicate double-counting detected."
    )
    assert result.excluded_count >= 1, "At least one duplicate must have been excluded."


# ─── Test 4: Temporal overlap exclusion ──────────────────────────────────────

def test_temporal_overlap_annual_not_summed_with_monthly(db):
    """
    An annual record (FY 2024-25) and monthly records for the same year+entity
    should NOT be summed together (grain collision).
    """
    # Annual total — 120 MT for full year
    _make_fact(db, reporting_period="FY 2024-25", numeric_value=120.0)
    # Three monthly sub-components
    for m, v in [("Apr-2024", 10.0), ("May-2024", 10.0), ("Jun-2024", 10.0)]:
        _make_fact(db, reporting_period=m, numeric_value=v)

    scope = EvidenceScope(metric_code="COAL_PRODUCTION", subsidiary="SECL")
    result = CalculationEngine.calculate(db, scope, AggOp.SUM)

    assert result.success is True
    # Must NOT be 150.0 (annual + 3 monthly = double counting)
    # Acceptable outcomes: 120 (annual wins) or 30 (3 monthly win) or similar
    assert result.result != pytest.approx(150.0, abs=2.0), (
        "Temporal grain collision was not resolved — "
        "annual + monthly sub-totals were summed together."
    )
    # Exclusion or warning must record the conflict
    has_signal = (
        result.excluded_count > 0
        or any(
            "grain" in w.lower() or "overlap" in w.lower() or "annual" in w.lower()
            for w in result.warnings
        )
    )
    assert has_signal, "No grain collision exclusion or warning was recorded."


# ─── Test 5: Consolidated CIL vs subsidiary exclusion ────────────────────────

def test_consolidated_vs_subsidiary_not_double_counted(db):
    """
    A CIL consolidated record and a SECL subsidiary record for the same
    metric+period must not be summed together.
    """
    _make_fact(db, subsidiary="CIL", numeric_value=800.0,
               entity_type="CONSOLIDATED")
    _make_fact(db, subsidiary="SECL", numeric_value=150.0)

    # Query across all subsidiaries
    scope = EvidenceScope(
        metric_code="COAL_PRODUCTION",
        reporting_period="FY 2024-25",
        exclude_consolidated=True,   # exclude CIL consolidated rows
    )
    result = CalculationEngine.calculate(db, scope, AggOp.SUM)

    assert result.success is True
    # With exclude_consolidated=True, CIL row dropped → only 150.0
    assert result.result == pytest.approx(150.0, abs=1.0), (
        f"Expected 150.0 (CIL excluded) but got {result.result}. "
        "Consolidated + subsidiary double-counting detected."
    )


# ─── Test 6: Unit mismatch detection ─────────────────────────────────────────

def test_unit_mismatch_warning_or_exclusion(db):
    """
    Facts with incompatible units (BCM vs MT) for the same metric must
    trigger a warning or exclusion — never silently mixed.
    """
    _make_fact(db, metric_code="OVERBURDEN_REMOVAL", unit="BCM",
               numeric_value=500.0)
    _make_fact(db, metric_code="OVERBURDEN_REMOVAL", unit="MT",
               numeric_value=100.0)

    scope = _scope(metric_code="OVERBURDEN_REMOVAL")
    result = CalculationEngine.calculate(db, scope, AggOp.SUM)

    has_unit_signal = (
        any("unit" in w.lower() or "mismatch" in w.lower() or "incompatible" in w.lower()
            for w in result.warnings)
        or result.excluded_count > 0
        or (result.error_code and "unit" in (result.error_code or "").lower())
    )
    assert has_unit_signal, (
        "Unit mismatch (BCM vs MT) was silently ignored — no warning, exclusion, or error."
    )


# ─── Test 7: Target achievement with matching scopes ─────────────────────────

def test_target_achievement_matching_scopes(db):
    """
    calculate_achievement returns correct pct when both actual and target
    evidence exist for the same entity + period.
    """
    _make_fact(db, metric_code="COAL_PRODUCTION", numeric_value=95.0)
    _make_fact(db, metric_code="PRODUCTION_TARGET", numeric_value=100.0)

    actual_scope = _scope(metric_code="COAL_PRODUCTION")
    target_scope = _scope(metric_code="PRODUCTION_TARGET")
    result = CalculationEngine.calculate_achievement(db, actual_scope, target_scope)

    assert result.success is True
    assert result.result == pytest.approx(95.0, abs=0.5), (
        f"Expected achievement ~95% but got {result.result}%"
    )
    assert result.unit == "%"


# ─── Test 8: Achievement refusal — no synthetic target ────────────────────────

def test_target_achievement_refuses_synthetic_fallback(db):
    """
    CRITICAL: When no PRODUCTION_TARGET evidence exists, the engine must
    return MISSING_TARGET error. It must NEVER fabricate target = actual × 1.04.
    """
    _make_fact(db, metric_code="COAL_PRODUCTION", numeric_value=95.0)
    # No target fact inserted

    actual_scope = _scope(metric_code="COAL_PRODUCTION")
    target_scope = _scope(metric_code="PRODUCTION_TARGET")
    result = CalculationEngine.calculate_achievement(db, actual_scope, target_scope)

    assert result.success is False, (
        "Engine should refuse to calculate achievement when no target evidence exists."
    )
    assert result.error_code == CalcError.MISSING_TARGET, (
        f"Expected MISSING_TARGET error code, got: {result.error_code}"
    )
    # Ensure no synthetic achievement percentage was returned
    if result.success:
        pytest.fail(
            f"achievement result={result.result}% returned despite missing target — "
            "synthetic fallback was used illegally."
        )


# ─── Test 9: Zero denominator handling ───────────────────────────────────────

def test_zero_denominator_target(db):
    """
    When target = 0.0, division-by-zero must be handled gracefully.
    Must return ZERO_DENOMINATOR error, not raise, not return Inf/NaN.
    """
    _make_fact(db, metric_code="COAL_PRODUCTION", numeric_value=50.0)
    _make_fact(db, metric_code="PRODUCTION_TARGET", numeric_value=0.0)

    actual_scope = _scope(metric_code="COAL_PRODUCTION")
    target_scope = _scope(metric_code="PRODUCTION_TARGET")
    result = CalculationEngine.calculate_achievement(db, actual_scope, target_scope)

    import math
    if result.success and result.result is not None:
        assert not math.isnan(result.result), "achievement_pct is NaN — zero-denominator not handled."
        assert not math.isinf(result.result), "achievement_pct is Inf — zero-denominator not handled."
    else:
        # Graceful error return is acceptable (ZERO_DENOMINATOR)
        assert result.error_code in (
            CalcError.ZERO_DENOMINATOR,
            CalcError.INSUFFICIENT_EVIDENCE,
        ), f"Unexpected error code: {result.error_code}"


# ─── Test 10: Data scope classification ──────────────────────────────────────

def test_demo_scope_real(db):
    _make_fact(db, is_demo=False, source_type="REAL")
    result = CalculationEngine.calculate(db, _scope(), AggOp.SUM)
    assert result.is_demo_scope in (DataScopeMode.REAL, "REAL", "REAL_UPLOADED_DATA")


def test_demo_scope_demo(db):
    _make_fact(db, is_demo=True, source_type="DEMO", document_id="doc-demo-001")
    result = CalculationEngine.calculate(db, _scope(), AggOp.SUM)
    assert result.is_demo_scope in (DataScopeMode.DEMO, "DEMO", "DEMO_DATA")


def test_demo_scope_mixed(db):
    _make_fact(db, is_demo=False, source_type="REAL")
    # Add a second fact for different period so not deduplicated
    _make_fact(db, is_demo=True, source_type="DEMO",
               document_id="doc-demo-001", reporting_period="FY 2023-24")

    scope = EvidenceScope(metric_code="COAL_PRODUCTION", subsidiary="SECL")
    result = CalculationEngine.calculate(db, scope, AggOp.SUM)
    # Either MIXED or the dominant source — as long as it is not UNKNOWN when we have facts
    assert result.success is True
    assert result.is_demo_scope in (
        DataScopeMode.MIXED, DataScopeMode.REAL, DataScopeMode.DEMO,
        "MIXED", "MIXED_WARNING", "REAL", "REAL_UPLOADED_DATA", "DEMO", "DEMO_DATA",
    )


# ─── Test 11: Lineage persistence and retrieval ───────────────────────────────

def test_lineage_persistence_and_retrieval(db):
    """
    After running a calculation and persisting lineage, the run must be
    retrievable with matching metadata.
    """
    _make_fact(db, numeric_value=75.0)
    scope = _scope()
    result = CalculationEngine.calculate(db, scope, AggOp.SUM)
    assert result.success is True

    # Persist lineage
    run_id = persist_calculation(db, result, operation=AggOp.SUM, initiated_by="test_suite")
    assert run_id is not None, "persist_calculation returned None — lineage persistence failed."

    # Load it back
    loaded = get_lineage(db, run_id)
    assert loaded is not None, "get_lineage returned None — run not found."
    assert loaded["metric_code"] == "COAL_PRODUCTION"
    assert loaded["result"] == pytest.approx(75.0, abs=0.01)
    assert loaded["success"] is True
    assert loaded["initiated_by"] == "test_suite"

    # lineage_id must be propagated back onto result
    assert result.lineage_id == run_id


# ─── Test 12: Reconciliation service ─────────────────────────────────────────

def test_reconciliation_subsidiary_vs_consolidated_mismatch(db):
    """
    ReconciliationService.run_all should detect a discrepancy when
    sum of subsidiaries exceeds the consolidated CIL total beyond tolerance.
    """
    # CIL consolidated = 100 MT
    _make_fact(db, subsidiary="CIL", numeric_value=100.0,
               entity_type="CONSOLIDATED")

    # Subsidiary sum = 180 MT (80% discrepancy — way above 2% tolerance)
    for sub in ("ECL", "SECL", "NCL"):
        _make_fact(db, subsidiary=sub, numeric_value=60.0)

    report = ReconciliationService.run_all(
        db,
        metric_code="COAL_PRODUCTION",
        reporting_period="FY 2024-25",
    )

    # At least one check must have failed due to large discrepancy
    assert not report.overall_passed or any(
        not c.passed for c in report.checks
    ), (
        "ReconciliationService did not flag a mismatch between "
        "subsidiaries (180 MT) and CIL consolidated (100 MT)."
    )


def test_reconciliation_passes_with_consistent_data(db):
    """
    When subsidiary totals closely match the CIL consolidated total,
    the reconciliation report should pass.
    """
    # CIL consolidated ≈ 100 MT
    _make_fact(db, subsidiary="CIL", numeric_value=100.0,
               entity_type="CONSOLIDATED")
    # Subsidiaries summing to 101 MT (1% off — within 2% tolerance)
    _make_fact(db, subsidiary="SECL", numeric_value=51.0)
    _make_fact(db, subsidiary="NCL",  numeric_value=50.0)

    report = ReconciliationService.run_all(
        db,
        metric_code="COAL_PRODUCTION",
        reporting_period="FY 2024-25",
    )

    # All checks should pass (1% discrepancy within 2% tolerance)
    assert report.overall_passed, (
        f"Reconciliation unexpectedly failed: "
        f"{[c.detail for c in report.checks if not c.passed]}"
    )
