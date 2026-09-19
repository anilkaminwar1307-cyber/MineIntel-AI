from typing import Optional, List
from pydantic import BaseModel


class QueryRequest(BaseModel):
    query: str
    scope: str = "ALL_EVIDENCE"  # CURRENT_DOCUMENT, SELECTED_DOCUMENTS, ALL_EVIDENCE
    response_mode: str = "STANDARD"  # STANDARD, OFFICIAL, PARLIAMENTARY
    document_ids: Optional[List[str]] = None


class CitationItem(BaseModel):
    document_id: str
    document_name: str
    page_number: Optional[int] = None
    sheet_name: Optional[str] = None
    cell_reference: Optional[str] = None
    metric_code: str
    value: str


class QueryResponse(BaseModel):
    query: str
    status: str  # "SUCCESS", "ERROR"
    answer: str
    scope: str = "ALL_EVIDENCE"
    response_mode: str = "STANDARD"
    calculation: Optional[str] = None
    records_used: int = 0
    # verified_facts_count is the frontend-facing alias for records_used
    verified_facts_count: int = 0
    verification_status: Optional[str] = None
    verification_result: Optional[str] = None
    confidence: float = 1.0
    confidence_score: Optional[float] = 1.0
    citations: List[CitationItem] = []
    sources: Optional[List[dict]] = []
    chart: Optional[dict] = None
    message: Optional[str] = None
    direct_metric_value: Optional[float] = None
    metric_unit: Optional[str] = None
    calculation_steps: Optional[List[str]] = None
    sql_query: Optional[str] = None
    suggestions: Optional[List[str]] = None

