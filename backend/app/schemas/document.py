from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, ConfigDict


class DocumentBase(BaseModel):
    original_filename: str
    file_type: str
    mime_type: str
    file_size: int
    document_category: Optional[str] = "General Mining Report"
    organization: str = "CMPDI / CIL"
    reporting_period: Optional[str] = None


class DocumentResponse(DocumentBase):
    id: str
    stored_filename: str
    storage_path: str
    source_type: Optional[str] = None
    quality_label: Optional[str] = None
    page_count: int = 0
    sheet_count: int = 0
    table_count: int = 0
    status: str
    processing_progress: int = 0
    processing_message: Optional[str] = None
    processing_error: Optional[str] = None
    fact_count: int = 0
    real_fact_count: int = 0
    warning_count: int = 0
    topic_count: int = 0
    is_demo: bool = False
    sha256: Optional[str] = None
    source_version: Optional[str] = "v1.0"
    revision_number: int = 1
    supersedes_document_id: Optional[str] = None
    is_latest_version: bool = True
    revision_date: Optional[datetime] = None
    pipeline_version: Optional[str] = "2.0"
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    created_at: datetime
    processed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentListResponse(BaseModel):
    items: List[DocumentResponse]
    total: int
    page: int = 1
    page_size: int = 50


class DocumentUploadResponse(BaseModel):
    message: str
    document: DocumentResponse
    is_duplicate: bool = False
    existing_document: Optional[DocumentResponse] = None


class BatchUploadItemResult(BaseModel):
    filename: str
    file_type: str
    file_size: int
    status: str
    document_id: Optional[str] = None
    is_duplicate: bool = False
    duplicate_of_id: Optional[str] = None
    duplicate_of_filename: Optional[str] = None
    detected_organization: Optional[str] = None
    detected_period: Optional[str] = None
    facts_extracted: int = 0
    warnings: List[str] = []
    error: Optional[str] = None


class BatchUploadResponse(BaseModel):
    total_files: int
    successful: int
    duplicates: int
    failed: int
    items: List[BatchUploadItemResult]


class DuplicateCheckResponse(BaseModel):
    is_duplicate: bool
    existing_document_id: Optional[str] = None
    existing_filename: Optional[str] = None
    existing_created_at: Optional[datetime] = None
    existing_facts_count: int = 0
    existing_status: Optional[str] = None
    message: Optional[str] = None


class ProcessingStatusResponse(BaseModel):
    document_id: str
    status: str
    processing_progress: int
    processing_message: Optional[str] = None
    current_stage: Optional[str] = None
    fact_count: int = 0
    warning_count: int = 0
    warnings: List[str] = []
    processing_error: Optional[str] = None
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None


class ExtractionSummaryResponse(BaseModel):
    document_id: str
    original_filename: str
    file_type: str
    document_category: Optional[str] = None
    organization: str
    reporting_period: Optional[str] = None
    quality_label: Optional[str] = None
    quality_score: Optional[float] = None
    page_count: int = 0
    sheet_count: int = 0
    table_count: int = 0
    total_facts: int = 0
    high_confidence_facts: int = 0
    needs_review_facts: int = 0
    conflicts_count: int = 0
    warning_count: int = 0
    warnings: List[str] = []
    is_demo: bool = False
    duration_seconds: Optional[float] = None


class SourcePreviewSheet(BaseModel):
    sheet_name: str
    used_range: Optional[str] = None
    headers: List[str] = []
    rows: List[List[Any]] = []
    row_count: int = 0
    col_count: int = 0


class SourcePreviewPage(BaseModel):
    page_number: int
    raw_text: Optional[str] = None
    has_native_text: bool = True
    is_ocr_page: bool = False
    ocr_confidence: Optional[float] = None
    extraction_method: Optional[str] = None


class SourcePreviewResponse(BaseModel):
    document_id: str
    original_filename: str
    file_type: str
    pages: List[SourcePreviewPage] = []
    sheets: List[SourcePreviewSheet] = []
    text_preview: Optional[str] = None


class MetadataUpdateRequest(BaseModel):
    document_category: Optional[str] = None
    organization: Optional[str] = None
    reporting_period: Optional[str] = None


class DocumentPageResponse(BaseModel):
    id: str
    document_id: str
    page_number: int
    raw_text: Optional[str] = None
    char_count: int = 0
    word_count: int = 0
    has_native_text: bool = True
    is_ocr_page: bool = False
    ocr_confidence: Optional[float] = None
    extraction_method: Optional[str] = "PDF_NATIVE"
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentSheetResponse(BaseModel):
    id: str
    document_id: str
    sheet_name: str
    sheet_index: int = 0
    row_count: int = 0
    col_count: int = 0
    used_range: Optional[str] = None
    header_row: Optional[int] = None
    has_merged_cells: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentTableResponse(BaseModel):
    id: str
    document_id: str
    sheet_id: Optional[str] = None
    table_index: int = 0
    source_type: str
    page_number: Optional[int] = None
    sheet_name: Optional[str] = None
    title: Optional[str] = None
    row_count: int = 0
    col_count: int = 0
    headers_json: Optional[str] = None
    data_json: Optional[str] = None
    confidence: float = 1.0
    structure_status: Optional[str] = "CLEAN"
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentChunkResponse(BaseModel):
    id: str
    document_id: str
    chunk_index: int
    page_number: Optional[int] = None
    sheet_name: Optional[str] = None
    section: Optional[str] = None
    content: str
    token_count: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentQualityResponse(BaseModel):
    id: str
    document_id: str
    quality_score: Optional[float] = None
    quality_label: Optional[str] = None
    enhancement_recommended: bool = False
    enhancement_applied: bool = False
    enhancement_methods: Optional[str] = None
    blur_level: Optional[str] = None
    contrast_level: Optional[str] = None
    noise_level: Optional[str] = None
    skew_angle: Optional[float] = None
    detected_dpi: Optional[int] = None
    quality_score_before: Optional[float] = None
    quality_score_after: Optional[float] = None
    ocr_confidence_before: Optional[float] = None
    ocr_confidence_after: Optional[float] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProcessingLogResponse(BaseModel):
    id: str
    document_id: str
    level: str
    stage: Optional[str] = None
    message: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentValidationIssueItem(BaseModel):
    id: str
    document_id: str
    fact_id: Optional[str] = None
    issue_type: str
    severity: str
    description: str
    is_resolved: bool
    created_at: datetime
    metric_name: Optional[str] = None
    numeric_value: Optional[float] = None
    unit: Optional[str] = None
    cell_reference: Optional[str] = None
    page_number: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentConflictItem(BaseModel):
    id: str
    metric_code: str
    primary_fact_id: str
    conflicting_fact_id: str
    description: str
    discrepancy_percent: Optional[float] = None
    status: str
    created_at: datetime
    primary_value: Optional[str] = None
    conflicting_value: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentValidationsResponse(BaseModel):
    document_id: str
    total_issues: int
    open_issues: int
    resolved_issues: int
    conflicts_count: int
    issues: List[DocumentValidationIssueItem] = []
    conflicts: List[DocumentConflictItem] = []

