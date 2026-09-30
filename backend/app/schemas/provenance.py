"""
EvidenceChain 2.0 — Universal Provenance & Claim Schemas.

Defines typed responses for:
- Universal EvidenceDrawer (Sections A-H)
- Surrounding Source Previews (PDF, Excel, CSV, OCR)
- Claims and ClaimEvidenceLinks
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict


# ─── Universal Provenance Response Sub-Models ───────────────────────────────

class SourceDocumentInfo(BaseModel):
    document_id: str
    document_name: str
    document_type: str
    document_category: Optional[str] = None
    organization: Optional[str] = "Coal India Limited"
    reporting_period: Optional[str] = None
    data_scope: str = "DEMO DATA"  # REAL UPLOADED DATA, DEMO DATA, MIXED
    is_demo: bool = False
    source_hash: Optional[str] = None
    pipeline_version: Optional[str] = "2.0"
    created_at: Optional[datetime] = None


class ProvenanceLocation(BaseModel):
    # PDF / Reports
    page_number: Optional[int] = None
    section_name: Optional[str] = None
    # Excel
    sheet_name: Optional[str] = None
    row_number: Optional[int] = None
    column_name: Optional[str] = None
    cell_reference: Optional[str] = None
    table_reference: Optional[str] = None
    # OCR / Image
    bounding_box: Optional[Dict[str, Any]] = None
    location_summary: str = "Exact coordinates tracked"


class RawEvidenceInfo(BaseModel):
    raw_cell_value: Optional[str] = None
    source_context: Optional[str] = None
    original_text: Optional[str] = None
    raw_unit: Optional[str] = None
    raw_metric_name: Optional[str] = None


class NormalizedFactInfo(BaseModel):
    id: str
    metric_code: str
    metric_name: str
    numeric_value: Optional[float] = None
    canonical_unit: Optional[str] = None
    reporting_period: Optional[str] = None
    organization: str
    subsidiary: Optional[str] = None
    coalfield: Optional[str] = None
    mine: Optional[str] = None
    temporal_grain: Optional[str] = None
    is_superseded: bool = False
    superseded_by_id: Optional[str] = None
    original_numeric_value: Optional[float] = None


class ExtractionInfo(BaseModel):
    extraction_method: str
    parser_method: Optional[str] = "Standard Table Parser"
    confidence_score: float = 1.0
    source_quality: str = "HIGH"
    pipeline_version: str = "2.0"
    dedup_key: Optional[str] = None


class ValidationInfo(BaseModel):
    machine_validation_status: str
    machine_confidence: float = 1.0
    validation_issues: List[Dict[str, Any]] = []
    conflict_status: str = "NONE"  # NONE, OPEN_CONFLICT, RESOLVED_CONFLICT
    is_duplicate: bool = False
    is_superseded: bool = False


class HumanReviewInfo(BaseModel):
    human_verified: bool = False
    verification_label: str = "Not Human Verified"  # "Verified by CMPDI Analyst" or "Not Human Verified"
    reviewer: Optional[str] = None
    verified_at: Optional[datetime] = None
    review_actions: List[Dict[str, Any]] = []


class UsageItem(BaseModel):
    id: str
    title: str
    type: str  # QUERY, CALCULATION, CHART, REPORT, REPORT_CLAIM
    timestamp: Optional[datetime] = None
    detail: Optional[str] = None


class UsageSummary(BaseModel):
    queries: List[UsageItem] = []
    calculations: List[UsageItem] = []
    charts: List[UsageItem] = []
    reports: List[UsageItem] = []


class UniversalProvenanceResponse(BaseModel):
    """
    Universal provenance payload powering EvidenceDrawer across all platform pages.
    """
    fact_id: str
    source: SourceDocumentInfo
    location: ProvenanceLocation
    raw_evidence: RawEvidenceInfo
    normalization: NormalizedFactInfo
    extraction: ExtractionInfo
    validation: ValidationInfo
    human_review: HumanReviewInfo
    conflicts: List[Dict[str, Any]] = []
    usage: UsageSummary
    data_scope: str = "DEMO DATA"  # REAL UPLOADED DATA / DEMO DATA / MIXED


# ─── Surrounding Source Context ──────────────────────────────────────────────

class SurroundingSourceResponse(BaseModel):
    document_id: str
    document_name: str
    document_type: str
    available: bool = True
    message: Optional[str] = None
    # For spreadsheets
    grid_rows: Optional[List[List[Any]]] = None
    grid_headers: Optional[List[str]] = None
    highlight_row: Optional[int] = None
    highlight_col: Optional[int] = None
    highlight_cell: Optional[str] = None
    sheet_name: Optional[str] = None
    # For PDF / text / OCR
    page_text: Optional[str] = None
    page_number: Optional[int] = None
    highlight_snippet: Optional[str] = None
    ocr_confidence: Optional[float] = None


# ─── Claims & Links ──────────────────────────────────────────────────────────

class ClaimCreateRequest(BaseModel):
    claim_type: str = "EVIDENCE_FACT"
    text: str
    query_id: Optional[str] = None
    report_id: Optional[str] = None
    confidence: float = 1.0
    fact_ids: List[str] = []
    calculation_id: Optional[str] = None


class ClaimResponse(BaseModel):
    id: str
    claim_type: str
    text: str
    query_id: Optional[str] = None
    report_id: Optional[str] = None
    support_status: str
    confidence: float
    created_at: datetime
    evidence_links: List[Dict[str, Any]] = []

    model_config = ConfigDict(from_attributes=True)
