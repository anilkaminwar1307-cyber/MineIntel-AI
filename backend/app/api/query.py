from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import require_analyst
from app.models.query import QueryHistory
from app.models.fact import ExtractedFact
from app.models.document import Document
from app.schemas.query import QueryRequest, QueryResponse, CitationItem, ClaimVerifyRequest
from app.services.intelligence.query_orchestrator import QueryOrchestrator
from app.services.intelligence.suggestions_engine import SuggestionsEngine
from app.services.calculations.lineage import get_lineage

router = APIRouter(prefix="/query", tags=["Ask MineIntel"])


@router.post("", response_model=QueryResponse)
def execute_query(
    request: QueryRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_analyst),
):
    """
    Primary intelligence query endpoint for Ask MineIntel.
    Routes queries through the 11-step QueryOrchestrator:
    - Zero-retrieval instant responses for greetings and capabilities
    - NumberSafe 2.0 deterministic SQL calculations
    - Hybrid BM25 retrieval for narrative questions
    - Grounded claim verification and conflict auditing
    - Full EvidenceChain granular provenance
    """
    user_name = current_user.get("full_name") or current_user.get("username") or "CMPDI Analyst"

    # Normalize include_demo from data_scope if supplied
    include_demo = request.include_demo
    if request.data_scope == "DEMO":
        include_demo = True
    elif request.data_scope == "REAL":
        include_demo = False

    result = QueryOrchestrator.process_query(
        db=db,
        query_text=request.query,
        scope=request.scope,
        response_mode=request.response_mode,
        subsidiary_filter=request.subsidiary,
        period_filter=request.period,
        document_ids=request.document_ids,
        only_verified=request.only_verified,
        include_demo=include_demo,
        session_id=request.session_id,
        user_name=user_name,
    )

    # Format citations for response schema
    citation_items = []
    for c in result.get("citations", []):
        citation_items.append(
            CitationItem(
                fact_id=c.get("fact_id"),
                document_id=str(c.get("document_id", "")),
                document_name=c.get("document_name", "Statutory Filing"),
                page_number=c.get("page_number"),
                sheet_name=c.get("sheet_name"),
                row_number=c.get("row_number"),
                column_name=c.get("column_name"),
                cell_reference=c.get("cell_reference"),
                metric_code=c.get("metric_code", "EVIDENCE"),
                metric_name=c.get("metric_name"),
                numeric_value=c.get("numeric_value"),
                unit=c.get("unit"),
                subsidiary=c.get("subsidiary"),
                reporting_period=c.get("reporting_period"),
                source_context=c.get("source_context"),
                confidence_score=c.get("confidence_score", 1.0),
                human_verified=c.get("human_verified", False),
                value=str(c.get("numeric_value") or c.get("value") or ""),
            )
        )

    records_used = result.get("records_used", 0)
    verified_count = result.get("verified_facts_count", 0)

    # Convert calculation_result if present
    calc_res_schema = None
    if result.get("calculation_result"):
        from app.services.query_engine import _calc_to_schema
        calc_res_schema = _calc_to_schema(result.get("calculation_result"))

    return QueryResponse(
        query_id=result.get("query_id"),
        query=request.query,
        status=result.get("status", "SUCCESS"),
        answer_status=result.get("answer_status", "SUCCESS"),
        intent=result.get("intent"),
        answer=result.get("answer", ""),
        scope=request.scope,
        response_mode=result.get("response_mode", request.response_mode),
        resolved_context=result.get("resolved_context"),
        confidence=result.get("confidence", 1.0),
        confidence_score=result.get("confidence_score", 1.0),
        confidence_level=result.get("confidence_level", "HIGH"),
        confidence_reason=result.get("confidence_reason"),
        confidence_details=result.get("confidence_details"),
        records_used=records_used,
        verified_facts_count=verified_count,
        verification_status=result.get("verification_status"),
        verification_result=result.get("verification_result"),
        citations=citation_items,
        sources=result.get("citations", []),
        calculation=result.get("calculation"),
        calculation_steps=result.get("calculation_steps"),
        calculation_result=calc_res_schema,
        direct_metric_value=result.get("direct_metric_value"),
        metric_unit=result.get("metric_unit"),
        sql_query=result.get("sql_query"),
        chart=result.get("chart"),
        key_figures=result.get("key_figures"),
        conflicts=result.get("conflicts"),
        data_scope=result.get("data_scope", "REAL UPLOADED DATA"),
        is_demo=result.get("is_demo", include_demo),
        execution_time_ms=result.get("execution_time_ms"),
        suggestions=result.get("suggested_followups"),
        suggested_followups=result.get("suggested_followups"),
    )


@router.get("/suggestions")
def get_suggestions(
    include_demo: bool = Query(default=False),
    limit: int = Query(default=6, ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_analyst),
):
    """
    Returns dynamically generated query suggestions backed by real database facts.
    """
    suggestions = SuggestionsEngine.get_dynamic_suggestions(db, include_demo=include_demo, limit=limit)
    return {"suggestions": suggestions, "count": len(suggestions), "data_scope": "DEMO" if include_demo else "REAL"}


@router.post("/verify-claim")
def verify_claim(
    request: ClaimVerifyRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_analyst),
):
    """
    Dedicated endpoint for auditing quantitative assertions against the ground truth Evidence Ledger.
    """
    from app.services.intelligence.claim_verifier import ClaimVerifier
    from app.services.intelligence.entity_resolver import MiningEntityResolver
    from app.services.intelligence.period_resolver import MiningPeriodResolver

    entity_info = MiningEntityResolver.resolve_entities(request.query)
    if request.subsidiary:
        entity_info["subsidiary"] = request.subsidiary.upper()
    if request.metric_code:
        entity_info["metric_code"] = request.metric_code

    period_info = MiningPeriodResolver.resolve_period(request.query)
    if request.period:
        period_info["period"] = request.period

    return ClaimVerifier.verify(
        db=db,
        query_text=request.query,
        entity_info=entity_info,
        period_info=period_info,
        only_verified=False,
        include_demo=request.include_demo,
    )


@router.get("/{query_id}/evidence")
def get_query_evidence(
    query_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_analyst),
):
    """
    Retrieves full evidence records utilized for a specific past query.
    """
    history = db.query(QueryHistory).filter(QueryHistory.id == query_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="Query history record not found")

    return {
        "query_id": history.id,
        "query_text": history.query_text,
        "scope": history.scope,
        "created_at": history.created_at,
        "citations": history.evidence_citations or "[]",
    }


@router.get("/{query_id}/calculation")
def get_query_calculation(
    query_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_analyst),
):
    """
    Retrieves NumberSafe 2.0 calculation lineage details associated with a query.
    """
    history = db.query(QueryHistory).filter(QueryHistory.id == query_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="Query history record not found")

    # Inspect lineage table for query reference or matching run
    from app.models.calculation import CalculationRun
    calc = db.query(CalculationRun).filter(CalculationRun.created_by.ilike(f"%{query_id}%")).first()
    if not calc:
        calc = db.query(CalculationRun).order_by(CalculationRun.created_at.desc()).first()

    if not calc:
        return {"query_id": query_id, "calculation_lineage": None, "message": "No calculation run associated with this query."}

    return get_lineage(db, calc.id)
