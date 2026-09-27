"""
NumberSafe 2.0 — Pydantic Schemas for Calculation API
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CalculationRequest(BaseModel):
    metric_code: str
    operation: str = "SUM"                    # SUM / LATEST / WAVG / AVG
    subsidiary: Optional[str] = None
    mine: Optional[str] = None
    reporting_period: Optional[str] = None
    only_verified: bool = False
    only_real: bool = False
    only_demo: bool = False
    exclude_consolidated: bool = True
    document_ids: Optional[List[str]] = None


class IncludedFactSchema(BaseModel):
    fact_id: str
    metric_code: str
    subsidiary: Optional[str] = None
    mine: Optional[str] = None
    reporting_period: Optional[str] = None
    numeric_value: Optional[float] = None
    unit: Optional[str] = None
    confidence_score: float
    validation_status: str
    is_demo: bool
    document_id: str
    page_number: Optional[int] = None
    sheet_name: Optional[str] = None
    cell_reference: Optional[str] = None
    source_context: Optional[str] = None


class ExclusionSchema(BaseModel):
    fact_id: str
    reason: str
    excluded_in_favour_of: Optional[str] = None


class CalculationResultSchema(BaseModel):
    success: bool
    error_code: Optional[str] = None
    error_message: Optional[str] = None

    result: Optional[float] = None
    unit: Optional[str] = None
    calculation_method: Optional[str] = None
    formula: Optional[str] = None

    metric_code: str
    filters_applied: Dict[str, Any] = {}

    evidence_count_total: int = 0
    evidence_count_used: int = 0
    excluded_count: int = 0
    verified_count: int = 0
    verified_pct: float = 0.0
    is_demo_scope: str = "UNKNOWN"

    included_facts: List[IncludedFactSchema] = []
    exclusions: List[ExclusionSchema] = []
    warnings: List[str] = []
    sql_description: str = ""
    lineage_id: Optional[str] = None


class LineageResponse(BaseModel):
    id: str
    operation: str
    metric_code: str
    filters: Dict[str, Any] = {}
    result: Optional[float] = None
    unit: Optional[str] = None
    formula: Optional[str] = None
    calculation_method: Optional[str] = None
    sql_description: Optional[str] = None
    success: bool
    error_code: Optional[str] = None
    evidence_count: int = 0
    evidence_used_count: int = 0
    verified_count: int = 0
    excluded_count: int = 0
    verified_pct: Optional[float] = None
    is_demo_scope: Optional[str] = None
    warnings: List[str] = []
    initiated_by: Optional[str] = None
    created_at: Optional[str] = None
    included_facts: List[Dict[str, Any]] = []
    excluded_facts: List[Dict[str, Any]] = []
