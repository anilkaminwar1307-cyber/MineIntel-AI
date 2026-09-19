from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class ExtractedFactResponse(BaseModel):
    id: str
    document_id: str
    metric_code: str
    metric_name: str
    raw_metric_name: Optional[str] = None
    numeric_value: Optional[float] = None
    text_value: Optional[str] = None
    unit: Optional[str] = None
    raw_unit: Optional[str] = None
    reporting_period: Optional[str] = None
    organization: str
    subsidiary: Optional[str] = None
    coalfield: Optional[str] = None
    mine: Optional[str] = None
    location: Optional[str] = None
    page_number: Optional[int] = None
    sheet_name: Optional[str] = None
    row_number: Optional[int] = None
    column_name: Optional[str] = None
    cell_reference: Optional[str] = None
    table_reference: Optional[str] = None
    source_context: Optional[str] = None
    extraction_method: str
    confidence_score: float
    validation_status: str
    human_verified: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExtractedFactListResponse(BaseModel):
    items: List[ExtractedFactResponse]
    total: int
    page: int = 1
    page_size: int = 50
    verified_count: int = 0
    needs_review_count: int = 0
    conflict_count: int = 0
