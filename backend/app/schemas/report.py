from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class GeneratedReportResponse(BaseModel):
    id: str
    title: str
    report_type: str
    parameters: Optional[str] = None
    status: str
    pdf_status: Optional[str] = "READY"
    summary: Optional[str] = None
    content_json: Optional[str] = None
    output_path: Optional[str] = None
    pdf_path: Optional[str] = None
    pdf_filename: Optional[str] = None
    pdf_size: Optional[int] = 0
    pdf_generated_at: Optional[datetime] = None
    evidence_count: int = 0
    generated_by: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GeneratePdfResponse(BaseModel):
    status: str
    report_id: str
    pdf_filename: str
    pdf_size: int
    pdf_url: str


class GenerateReportRequest(BaseModel):
    title: Optional[str] = None
    report_type: str = "Production Summary"
    subsidiary: str = "ALL"
    period: str = "FY 2024-25"
    document_ids: Optional[List[str]] = None
    only_verified: bool = True
    generated_by: Optional[str] = "CMPDI Senior Analyst"
    draft_override: bool = False  # Allows exporting DRAFT — UNVERIFIED if ReportGuard is BLOCKED


class GeneratedReportListResponse(BaseModel):
    items: List[GeneratedReportResponse]
    total: int
    available_templates: List[str]


class ReportGuardRequest(BaseModel):
    report_type: Optional[str] = "Production Summary"
    subsidiary: Optional[str] = "ALL"
    period: Optional[str] = "ALL"
    only_verified: Optional[bool] = True
    document_ids: Optional[List[str]] = None


class EvidenceRegisterItem(BaseModel):
    evidence_id: str
    claim_metric: str
    value: float
    unit: str
    document_name: str
    source_location: str
    validation_status: str
    human_verified: bool
    calculation_id: Optional[str] = None
    fact_id: str


