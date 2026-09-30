from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, ConfigDict


class ReviewItemResponse(BaseModel):
    id: str
    document_id: str
    fact_id: Optional[str] = None
    issue_type: str
    severity: str
    description: str
    is_resolved: bool
    created_at: datetime
    
    # Context if available
    metric_name: Optional[str] = None
    numeric_value: Optional[float] = None
    unit: Optional[str] = None
    subsidiary: Optional[str] = None
    reporting_period: Optional[str] = None
    confidence_score: Optional[float] = None
    source_reference: Optional[str] = None
    document_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ConflictItemResponse(BaseModel):
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
    subsidiary: Optional[str] = None
    period: Optional[str] = None


class ReviewQueueResponse(BaseModel):
    open_reviews: int = 0
    conflicts: int = 0
    low_confidence: int = 0
    missing_metadata: int = 0
    total: int = 0
    page: int = 1
    page_size: int = 50
    items: List[ReviewItemResponse] = []
    conflict_items: List[ConflictItemResponse] = []


class ReviewApproveRequest(BaseModel):
    notes: Optional[str] = "Approved by CMPDI Analyst"
    reviewer_name: Optional[str] = "CMPDI Analyst"


class ReviewRejectRequest(BaseModel):
    notes: str = "Rejected during human review"
    reviewer_name: Optional[str] = "CMPDI Analyst"


class ReviewEditRequest(BaseModel):
    numeric_value: Optional[float] = None
    corrected_value: Optional[float] = None
    metric_code: Optional[str] = None
    metric_name: Optional[str] = None
    unit: Optional[str] = None
    reporting_period: Optional[str] = None
    subsidiary: Optional[str] = None
    mine: Optional[str] = None
    coalfield: Optional[str] = None
    notes: Optional[str] = "Value corrected by CMPDI Analyst"
    reviewer_name: Optional[str] = "CMPDI Analyst"

    def get_value(self) -> float:
        if self.numeric_value is not None:
            return self.numeric_value
        if self.corrected_value is not None:
            return self.corrected_value
        return 0.0


class FactEditAndApproveRequest(BaseModel):
    numeric_value: float
    metric_code: Optional[str] = None
    metric_name: Optional[str] = None
    unit: Optional[str] = None
    reporting_period: Optional[str] = None
    organization: Optional[str] = None
    subsidiary: Optional[str] = None
    coalfield: Optional[str] = None
    mine: Optional[str] = None
    notes: Optional[str] = "Corrected and verified by CMPDI Analyst"
    reviewer_name: Optional[str] = "CMPDI Analyst"


class ConflictResolveRequest(BaseModel):
    winning_fact_id: Optional[str] = None
    chosen_fact_id: Optional[str] = None
    resolution_action: Optional[str] = "ACCEPT_CHOSEN"  # ACCEPT_CHOSEN, MARK_SUPERSEDED, MARK_DUPLICATE, MANUAL_OVERRIDE
    resolution_notes: str = "Conflict resolved by CMPDI Analyst"
    reviewer_name: Optional[str] = "CMPDI Analyst"
    corrected_value: Optional[float] = None

    def get_winning_id(self) -> str:
        return self.winning_fact_id or self.chosen_fact_id or ""


class ReviewActionResponse(BaseModel):
    id: str
    fact_id: Optional[str] = None
    conflict_id: Optional[str] = None
    reviewer_name: str
    action: str
    previous_value: Optional[str] = None
    new_value: Optional[str] = None
    previous_metric: Optional[str] = None
    new_metric: Optional[str] = None
    previous_unit: Optional[str] = None
    new_unit: Optional[str] = None
    previous_status: Optional[str] = None
    new_status: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

