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
    topic_count: int = 0
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
