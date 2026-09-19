from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel


class OverviewKPIs(BaseModel):
    documents_processed: int = 0
    facts_extracted: int = 0
    verified_evidence: int = 0
    pending_reviews: int = 0
    true_conflicts: int = 0
    average_confidence: float = 0.0
    reports_generated: int = 0
    active_subsidiaries: int = 0


class SubsidiarySummary(BaseModel):
    subsidiary: str
    fact_count: int
    coalfield_count: int
    production_mt: Optional[float] = 0.0


class MetricDistribution(BaseModel):
    metric_code: str
    metric_name: str
    count: int


class ChartDataPoint(BaseModel):
    label: str
    value: float
    secondary_value: Optional[float] = None
    category: Optional[str] = None


class AnalyticsOverviewResponse(BaseModel):
    kpis: OverviewKPIs
    subsidiaries: List[SubsidiarySummary] = []
    top_metrics: List[MetricDistribution] = []
    production_trends: List[Dict[str, Any]] = []
    multi_year_production_trends: List[Dict[str, Any]] = []
    target_vs_achievement: List[Dict[str, Any]] = []
    production_vs_dispatch: List[Dict[str, Any]] = []
    # confidence_distribution is a dict: {high_confidence: N, medium_confidence: N, low_confidence: N}
    confidence_distribution: Union[Dict[str, Any], List[Dict[str, Any]]] = {}
    issue_distribution: List[Dict[str, Any]] = []
    available_financial_years: List[str] = []
    available_subsidiaries: List[str] = []
    recent_activity_count: int = 0


class ExtendedAnalyticsResponse(BaseModel):
    """14 additional chart datasets for the expanded Analytics page."""
    production_growth_yoy: List[Dict[str, Any]] = []
    metric_type_breakdown: List[Dict[str, Any]] = []
    subsidiary_fact_share: List[Dict[str, Any]] = []
    extraction_method_mix: List[Dict[str, Any]] = []
    monthly_uploads: List[Dict[str, Any]] = []
    coalfield_production: List[Dict[str, Any]] = []
    verification_rate_by_sub: List[Dict[str, Any]] = []
    stripping_ratio_trend: List[Dict[str, Any]] = []
    confidence_histogram: List[Dict[str, Any]] = []
    top_mines: List[Dict[str, Any]] = []
    offtake_gap: List[Dict[str, Any]] = []
    issue_type_dist: List[Dict[str, Any]] = []
    doc_type_mix: List[Dict[str, Any]] = []
    audit_activity_trend: List[Dict[str, Any]] = []
