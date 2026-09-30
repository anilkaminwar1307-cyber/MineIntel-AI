"""
NumberSafe 2.0 — Calculations API Router

POST /api/calculations/run      — execute deterministic calculation
GET  /api/calculations/{id}     — retrieve result by lineage ID
GET  /api/calculations/{id}/lineage — full trace with included/excluded facts
POST /api/calculations/achieve  — compute target achievement (with scope validation)
POST /api/calculations/reconcile — run reconciliation checks
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.calculation import (
    CalculationRequest,
    CalculationResultSchema,
    ExclusionSchema,
    IncludedFactSchema,
    LineageResponse,
)
from app.services.calculations.calculation_engine import (
    CalculationEngine,
    CalcError,
    EvidenceScope,
)
from app.services.calculations.lineage import get_lineage, persist_calculation
from app.services.calculations.metric_semantics import AggOp
from app.services.calculations.reconciliation import ReconciliationService

router = APIRouter(prefix="/calculations", tags=["NumberSafe Calculations"])


def _scope_from_req(req: CalculationRequest) -> EvidenceScope:
    return EvidenceScope(
        metric_code=req.metric_code,
        subsidiary=req.subsidiary,
        mine=req.mine,
        reporting_period=req.reporting_period,
        only_verified=req.only_verified,
        only_real=req.only_real,
        only_demo=req.only_demo,
        exclude_consolidated=req.exclude_consolidated,
        document_ids=req.document_ids,
    )


def _result_to_schema(result) -> CalculationResultSchema:
    return CalculationResultSchema(
        success=result.success,
        error_code=result.error_code,
        error_message=result.error_message,
        result=result.result,
        unit=result.unit,
        calculation_method=result.calculation_method,
        formula=result.formula,
        metric_code=result.metric_code,
        filters_applied=result.filters_applied,
        evidence_count_total=result.evidence_count_total,
        evidence_count_used=result.evidence_count_used,
        excluded_count=result.excluded_count,
        verified_count=result.verified_count,
        verified_pct=result.verified_pct,
        is_demo_scope=result.is_demo_scope,
        included_facts=[
            IncludedFactSchema(**{k: v for k, v in inc.__dict__.items()})
            for inc in result.included_facts
        ],
        exclusions=[
            ExclusionSchema(
                fact_id=exc.fact_id,
                reason=exc.reason,
                excluded_in_favour_of=exc.excluded_in_favour_of,
            )
            for exc in result.exclusions
        ],
        warnings=result.warnings,
        sql_description=result.sql_description,
        lineage_id=result.lineage_id,
    )


@router.post("/run", response_model=CalculationResultSchema, summary="Run deterministic calculation")
@router.post("/calculate", response_model=CalculationResultSchema, summary="Run deterministic calculation (alias)")
def run_calculation(req: CalculationRequest, db: Session = Depends(get_db)):
    """
    Execute a deterministic NumberSafe calculation.
    Returns the full result with included facts, excluded facts, and lineage.
    """
    scope = _scope_from_req(req)
    result = CalculationEngine.calculate(db, scope, operation=req.operation)
    persist_calculation(db, result, operation=req.operation)
    try:
        db.commit()
    except Exception:
        db.rollback()
    return _result_to_schema(result)


@router.post("/achieve", response_model=CalculationResultSchema, summary="Compute target achievement %")
@router.post("/achievement", response_model=CalculationResultSchema, summary="Compute target achievement % (alias)")
def run_achievement(
    actual_req: CalculationRequest,
    target_metric_code: str = "PRODUCTION_TARGET",
    db: Session = Depends(get_db),
):
    """
    Compute (actual/target)*100 with full scope validation.
    Returns MISSING_TARGET error if no target evidence exists — never synthesises.
    """
    actual_scope = _scope_from_req(actual_req)
    target_scope = EvidenceScope(
        metric_code=target_metric_code,
        subsidiary=actual_scope.subsidiary,
        mine=actual_scope.mine,
        reporting_period=actual_scope.reporting_period,
        only_verified=actual_scope.only_verified,
        only_real=actual_scope.only_real,
        only_demo=actual_scope.only_demo,
        exclude_consolidated=actual_scope.exclude_consolidated,
    )
    result = CalculationEngine.calculate_achievement(db, actual_scope, target_scope)
    persist_calculation(db, result, operation="RATIO")
    try:
        db.commit()
    except Exception:
        db.rollback()
    return _result_to_schema(result)


@router.get("/{lineage_id}", response_model=CalculationResultSchema, summary="Get calculation by lineage ID")
def get_calculation(lineage_id: str, db: Session = Depends(get_db)):
    """Retrieve a previously computed calculation result by its lineage ID."""
    data = get_lineage(db, lineage_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Calculation '{lineage_id}' not found.")

    return CalculationResultSchema(
        success=data.get("success", False),
        error_code=data.get("error_code"),
        result=data.get("result"),
        unit=data.get("unit"),
        formula=data.get("formula"),
        calculation_method=data.get("calculation_method"),
        metric_code=data.get("metric_code", ""),
        filters_applied=data.get("filters", {}),
        evidence_count_total=data.get("evidence_count", 0),
        evidence_count_used=data.get("evidence_used_count", 0),
        excluded_count=data.get("excluded_count", 0),
        verified_count=data.get("verified_count", 0),
        verified_pct=data.get("verified_pct") or 0.0,
        is_demo_scope=data.get("is_demo_scope") or "UNKNOWN",
        warnings=data.get("warnings", []),
        sql_description=data.get("sql_description") or "",
        lineage_id=lineage_id,
    )


@router.get("/{lineage_id}/lineage", response_model=LineageResponse, summary="Get full calculation lineage trace")
def get_calculation_lineage(lineage_id: str, db: Session = Depends(get_db)):
    """
    Full audit trace: filters, formula, included facts, excluded facts with reasons.
    Used by the frontend 'How was this calculated?' expandable section.
    """
    data = get_lineage(db, lineage_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Lineage '{lineage_id}' not found.")
    return LineageResponse(**data)


@router.get("/reconcile", summary="Run deterministic reconciliation checks (GET)")
@router.post("/reconcile", summary="Run deterministic reconciliation checks (POST)")
def run_reconciliation(
    metric_code: str = "COAL_PRODUCTION",
    reporting_period: Optional[str] = None,
    only_verified: bool = False,
    db: Session = Depends(get_db),
):
    """
    Runs subsidiary-sum vs consolidated reconciliation.
    Returns a list of checks with pass/fail and discrepancy details.
    """
    report = ReconciliationService.run_all(
        db,
        metric_code=metric_code,
        reporting_period=reporting_period,
        only_verified=only_verified,
    )
    return {
        "overall_passed": report.overall_passed,
        "checks": [
            {
                "name": c.name,
                "passed": c.passed,
                "detail": c.detail,
                "lhs_value": c.lhs_value,
                "rhs_value": c.rhs_value,
                "tolerance_pct": c.tolerance_pct,
                "discrepancy_pct": c.discrepancy_pct,
            }
            for c in report.checks
        ],
        "issues": [c.detail for c in report.checks if not c.passed],
        "total": len(report.checks),
    }


@router.get("/{id}/evidence", summary="Get evidence bundle for a calculation run")
def get_calculation_evidence(id: str, db: Session = Depends(get_db)):
    """
    EvidenceChain 2.0: Returns full underlying evidence facts used in this computation.
    Enables clicking any fact in the calculation trace to open its EvidenceDrawer.
    """
    from app.models.fact import ExtractedFact
    from app.models.document import Document

    data = get_lineage(db, id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Calculation run '{id}' not found.")

    included = data.get("included_facts", [])
    excluded = data.get("exclusions", [])

    # Enrich included facts with document names if missing
    doc_cache = {}
    enriched_included = []
    for inc in included:
        doc_id = inc.get("document_id")
        doc_name = "CMPDI Document"
        if doc_id:
            if doc_id not in doc_cache:
                doc = db.query(Document).filter(Document.id == doc_id).first()
                doc_cache[doc_id] = doc.original_filename if doc else "Document"
            doc_name = doc_cache[doc_id]
        
        inc_copy = dict(inc)
        inc_copy["document_name"] = doc_name
        enriched_included.append(inc_copy)

    return {
        "calculation_id": id,
        "operation": data.get("operation") or "SUM",
        "metric_code": data.get("metric_code"),
        "result": data.get("result"),
        "unit": data.get("unit"),
        "formula": data.get("formula"),
        "sql_description": data.get("sql_description"),
        "data_scope": data.get("is_demo_scope") or "DEMO",
        "verified_pct": data.get("verified_pct") or 0.0,
        "evidence_count_total": data.get("evidence_count", 0),
        "evidence_count_used": data.get("evidence_used_count", 0),
        "excluded_count": data.get("excluded_count", 0),
        "included_facts": enriched_included,
        "exclusions": excluded,
        "warnings": data.get("warnings", [])
    }
