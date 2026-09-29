from typing import Optional, List, Dict, Any
from pydantic import BaseModel

from app.schemas.calculation import CalculationResultSchema


class QueryRequest(BaseModel):
    query: str
    scope: str = "ALL_EVIDENCE"  # ALL_EVIDENCE, SELECTED_DOCUMENTS, VERIFIED_ONLY
    response_mode: str = "STANDARD"  # STANDARD, QUICK, DETAILED, PARLIAMENTARY, VERIFICATION, COMPARISON, ANALYST
    document_ids: Optional[List[str]] = None
    subsidiary: Optional[str] = None
    period: Optional[str] = None
    only_verified: bool = False
    include_demo: bool = False
    data_scope: Optional[str] = "REAL"  # REAL, DEMO, ALL
    session_id: Optional[str] = None


class ClaimVerifyRequest(BaseModel):
    query: str
    claimed_value: Optional[float] = None
    unit: Optional[str] = None
    subsidiary: Optional[str] = None
    period: Optional[str] = None
    metric_code: Optional[str] = None
    include_demo: bool = False


class CitationItem(BaseModel):
    fact_id: Optional[str] = None
    document_id: str
    document_name: str
    page_number: Optional[int] = None
    sheet_name: Optional[str] = None
    row_number: Optional[int] = None
    column_name: Optional[str] = None
    cell_reference: Optional[str] = None
    metric_code: str
    metric_name: Optional[str] = None
    numeric_value: Optional[float] = None
    unit: Optional[str] = None
    subsidiary: Optional[str] = None
    reporting_period: Optional[str] = None
    source_context: Optional[str] = None
    confidence_score: Optional[float] = 1.0
    human_verified: Optional[bool] = False
    value: Optional[str] = None


class QueryResponse(BaseModel):
    query_id: Optional[str] = None
    query: str
    status: str  # "SUCCESS", "INSUFFICIENT_EVIDENCE", "ERROR", etc.
    answer_status: Optional[str] = "SUCCESS"
    intent: Optional[str] = None
    answer: str
    scope: str = "ALL_EVIDENCE"
    response_mode: str = "STANDARD"
    resolved_context: Optional[Dict[str, Any]] = None

    # Confidence scoring
    confidence: float = 1.0
    confidence_score: Optional[float] = 1.0
    confidence_level: Optional[str] = "HIGH"
    confidence_reason: Optional[str] = None
    confidence_details: Optional[Dict[str, Any]] = None

    # Evidence & Verification counts
    records_used: int = 0
    verified_facts_count: int = 0
    verification_status: Optional[str] = None
    verification_result: Optional[str] = None

    # Citations
    citations: List[CitationItem] = []
    sources: Optional[List[dict]] = []

    # NumberSafe & Calculation details
    calculation: Optional[str] = None
    calculation_steps: Optional[List[str]] = None
    calculation_result: Optional[CalculationResultSchema] = None
    direct_metric_value: Optional[float] = None
    metric_unit: Optional[str] = None
    sql_query: Optional[str] = None

    # Visualizations & Key figures
    chart: Optional[dict] = None
    key_figures: Optional[List[Dict[str, Any]]] = None
    conflicts: Optional[List[Dict[str, Any]]] = None

    # Scope & Execution
    data_scope: Optional[str] = "REAL UPLOADED DATA"
    is_demo: bool = False
    execution_time_ms: Optional[float] = None

    # Dynamic suggestions
    suggestions: Optional[List[str]] = None
    suggested_followups: Optional[List[str]] = None
    message: Optional[str] = None
