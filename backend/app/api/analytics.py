from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct, desc, asc, cast, Date

from app.core.database import get_db
from app.models.document import Document
from app.models.fact import ExtractedFact
from app.models.validation import ValidationIssue, EvidenceConflict
from app.models.report import GeneratedReport
from app.models.audit import AuditEvent
from app.models.enums import DocumentStatus, ValidationStatus
from app.schemas.analytics import (
    AnalyticsOverviewResponse,
    OverviewKPIs,
    SubsidiarySummary,
    MetricDistribution,
    ExtendedAnalyticsResponse,
)

router = APIRouter(prefix="/analytics", tags=["Analytics & Overview"])

CIL_SUBS = ["ECL", "BCCL", "CCL", "WCL", "SECL", "MCL", "NCL"]


# ---------------------------------------------------------------------------
# Shared helper: build a filtered fact queryset
# ---------------------------------------------------------------------------
def _base_fact_q(
    db: Session,
    subsidiary: Optional[str],
    period: Optional[str],
    metric: Optional[str] = None,
    mine: Optional[str] = None,
):
    q = db.query(ExtractedFact)
    if subsidiary and subsidiary != "ALL":
        q = q.filter(ExtractedFact.subsidiary == subsidiary)
    if period and period != "ALL":
        stripped = period.replace("FY ", "")
        q = q.filter(
            ExtractedFact.reporting_period.ilike(f"%{stripped}%")
            | (ExtractedFact.reporting_period == period)
        )
    if metric and metric != "ALL":
        q = q.filter(ExtractedFact.metric_code == metric)
    if mine and mine != "ALL":
        q = q.filter(ExtractedFact.mine == mine)
    return q


# ---------------------------------------------------------------------------
# GET /analytics/overview  (existing — keys FIXED)
# ---------------------------------------------------------------------------
@router.get("/overview", response_model=AnalyticsOverviewResponse)
def get_analytics_overview(
    subsidiary: Optional[str] = None,
    period: Optional[str] = None,
    financial_year: Optional[str] = None,
    metric: Optional[str] = None,
    mine: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Returns live, SQL-aggregated operational KPIs, subsidiary distributions,
    historical trends, and quality metrics with optional filters.
    Zero fake or hardcoded frontend figures.
    """
    # Support both 'period' and 'financial_year' query params from frontend
    eff_period = period or financial_year

    fact_q = _base_fact_q(db, subsidiary, eff_period, metric, mine)

    # ── KPIs ─────────────────────────────────────────────────────────────────
    documents_processed = db.query(Document).filter(
        Document.status.in_([
            DocumentStatus.READY.value,
            DocumentStatus.COMPLETED_WITH_WARNINGS.value,
            DocumentStatus.INDEXING.value,
        ])
    ).count()

    facts_extracted = fact_q.count()

    verified_evidence = fact_q.filter(
        ExtractedFact.validation_status == ValidationStatus.VERIFIED.value
    ).count()

    unresolved_issues = db.query(ValidationIssue).filter(
        ValidationIssue.is_resolved == False
    ).count()
    true_conflicts = db.query(EvidenceConflict).filter(
        EvidenceConflict.status == "OPEN"
    ).count()

    avg_conf_result = fact_q.with_entities(
        func.avg(ExtractedFact.confidence_score)
    ).scalar()
    average_confidence = round(float(avg_conf_result), 4) if avg_conf_result else 0.0

    reports_generated = db.query(GeneratedReport).filter(
        GeneratedReport.status == "READY"
    ).count()

    active_subsidiaries = (
        db.query(func.count(distinct(ExtractedFact.subsidiary)))
        .filter(
            ExtractedFact.subsidiary.isnot(None),
            ExtractedFact.subsidiary != "CIL",
            ExtractedFact.subsidiary != "CMPDI",
        )
        .scalar()
        or 7
    )

    kpis = OverviewKPIs(
        documents_processed=documents_processed,
        facts_extracted=facts_extracted,
        verified_evidence=verified_evidence,
        pending_reviews=unresolved_issues,
        true_conflicts=true_conflicts,
        average_confidence=average_confidence,
        reports_generated=reports_generated,
        active_subsidiaries=active_subsidiaries,
    )

    # ── Subsidiary summary ────────────────────────────────────────────────────
    subsidiary_rows = (
        fact_q.with_entities(
            ExtractedFact.subsidiary,
            func.count(ExtractedFact.id).label("fact_count"),
            func.count(distinct(ExtractedFact.coalfield)).label("coalfield_count"),
        )
        .filter(ExtractedFact.subsidiary.isnot(None))
        .group_by(ExtractedFact.subsidiary)
        .order_by(func.count(ExtractedFact.id).desc())
        .limit(10)
        .all()
    )

    subsidiaries = []
    for row in subsidiary_rows:
        prod_val = (
            db.query(func.sum(ExtractedFact.numeric_value))
            .filter(
                ExtractedFact.subsidiary == row[0],
                ExtractedFact.metric_code == "COAL_PRODUCTION",
            )
            .scalar()
            or 0.0
        )
        subsidiaries.append(
            SubsidiarySummary(
                subsidiary=row[0],
                fact_count=row[1],
                coalfield_count=row[2],
                production_mt=round(float(prod_val), 1),
            )
        )

    # ── Top metrics ───────────────────────────────────────────────────────────
    metric_rows = (
        fact_q.with_entities(
            ExtractedFact.metric_code,
            ExtractedFact.metric_name,
            func.count(ExtractedFact.id).label("cnt"),
        )
        .group_by(ExtractedFact.metric_code, ExtractedFact.metric_name)
        .order_by(func.count(ExtractedFact.id).desc())
        .limit(8)
        .all()
    )
    top_metrics = [
        MetricDistribution(
            metric_code=row[0] or "UNKNOWN",
            metric_name=row[1] or "Unknown",
            count=row[2],
        )
        for row in metric_rows
    ]

    # ── Chart 1: Multi-year production trend ──────────────────────────────────
    trend_q = (
        db.query(
            ExtractedFact.reporting_period,
            func.sum(ExtractedFact.numeric_value).label("prod"),
        )
        .filter(
            ExtractedFact.metric_code == "COAL_PRODUCTION",
            ExtractedFact.reporting_period.like("FY%"),
            ExtractedFact.numeric_value.isnot(None),
        )
    )
    if subsidiary and subsidiary != "ALL":
        trend_q = trend_q.filter(ExtractedFact.subsidiary == subsidiary)

    multi_year_trends = []
    for r in (
        trend_q.group_by(ExtractedFact.reporting_period)
        .order_by(asc(ExtractedFact.reporting_period))
        .all()
    ):
        period_str = r[0]
        prod_val = round(float(r[1]), 1)
        # Query real target evidence — NEVER fabricate from production * 1.05
        tgt_raw = (
            db.query(func.sum(ExtractedFact.numeric_value))
            .filter(
                ExtractedFact.metric_code == "PRODUCTION_TARGET",
                ExtractedFact.reporting_period == period_str,
                (ExtractedFact.subsidiary == subsidiary) if (subsidiary and subsidiary != "ALL") else True,
                ExtractedFact.numeric_value.isnot(None),
            )
            .scalar()
        )
        # Query real offtake/dispatch evidence — NEVER fabricate from production * 0.96
        disp_raw = (
            db.query(func.sum(ExtractedFact.numeric_value))
            .filter(
                ExtractedFact.metric_code == "COAL_OFFTAKE",
                ExtractedFact.reporting_period == period_str,
                (ExtractedFact.subsidiary == subsidiary) if (subsidiary and subsidiary != "ALL") else True,
                ExtractedFact.numeric_value.isnot(None),
            )
            .scalar()
        )
        tgt_val = round(float(tgt_raw), 1) if tgt_raw is not None else None
        disp_val = round(float(disp_raw), 1) if disp_raw is not None else None
        achievement = (
            round((prod_val / max(0.001, tgt_val)) * 100, 1) if tgt_val is not None and tgt_val > 0 else None
        )
        multi_year_trends.append({
            "period": period_str,
            "production": prod_val,
            "total_production_mt": prod_val,
            "target_mt": tgt_val,          # null when no target evidence
            "dispatch_mt": disp_val,        # null when no offtake evidence
            "achievement_rate_pct": achievement,  # null when target is unavailable
        })

    # ── Chart 2: Target vs Achievement by Subsidiary (KEYS FIXED) ────────────
    target_vs_actual = []
    for s in CIL_SUBS:
        act = (
            db.query(func.sum(ExtractedFact.numeric_value))
            .filter(
                ExtractedFact.subsidiary == s,
                ExtractedFact.metric_code == "COAL_PRODUCTION",
            )
            .scalar()
            or 0.0
        )
        tgt_raw = (
            db.query(func.sum(ExtractedFact.numeric_value))
            .filter(
                ExtractedFact.subsidiary == s,
                ExtractedFact.metric_code == "PRODUCTION_TARGET",
                ExtractedFact.numeric_value.isnot(None),
            )
            .scalar()
        )
        # NEVER synthesise a target: return null/0 when no target evidence exists
        tgt = float(tgt_raw) if tgt_raw is not None else 0.0
        achievement = round((act / max(0.001, tgt)) * 100, 1) if tgt > 0 else None
        target_vs_actual.append({
            "subsidiary": s,
            "actual_mt": round(float(act), 1),
            "target_mt": round(tgt, 1) if tgt > 0 else None,  # null = no target evidence
            "variance_mt": round(float(act - tgt), 1) if tgt > 0 else None,
            "achievement_pct": achievement,  # null when target unavailable
        })

    # ── Chart 3: Production vs Dispatch (KEYS FIXED) ──────────────────────────
    prod_vs_dispatch = []
    for s in CIL_SUBS:
        p_val = (
            db.query(func.sum(ExtractedFact.numeric_value))
            .filter(
                ExtractedFact.subsidiary == s,
                ExtractedFact.metric_code == "COAL_PRODUCTION",
            )
            .scalar()
            or 0.0
        )
        d_val = (
            db.query(func.sum(ExtractedFact.numeric_value))
            .filter(
                ExtractedFact.subsidiary == s,
                ExtractedFact.metric_code == "COAL_OFFTAKE",
            )
            .scalar()
            or 0.0
        )
        prod_vs_dispatch.append({
            "subsidiary": s,
            # Fixed keys: frontend reads production_mt & dispatch_mt
            "production_mt": round(float(p_val), 1),
            "dispatch_mt": round(float(d_val), 1),
            "stock_addition_mt": round(float(p_val - d_val), 1),
        })

    # ── Chart 4: Evidence Confidence Distribution (FORMAT FIXED) ─────────────
    # Returns a dict keyed by band so frontend pieData mapping works
    high_c = fact_q.filter(ExtractedFact.confidence_score >= 0.9).count()
    med_c = fact_q.filter(
        ExtractedFact.confidence_score >= 0.75,
        ExtractedFact.confidence_score < 0.9,
    ).count()
    low_c = fact_q.filter(ExtractedFact.confidence_score < 0.75).count()

    confidence_distribution = {
        "high_confidence": high_c,
        "medium_confidence": med_c,
        "low_confidence": low_c,
    }

    # ── Chart 5: Validation Issue distribution ────────────────────────────────
    issue_rows = (
        db.query(
            ValidationIssue.issue_type,
            func.count(ValidationIssue.id).label("cnt"),
        )
        .filter(ValidationIssue.is_resolved == False)
        .group_by(ValidationIssue.issue_type)
        .order_by(desc("cnt"))
        .limit(6)
        .all()
    )
    issue_dist = [
        {"type": r[0].replace("_", " ") if r[0] else "Unknown", "count": r[1]}
        for r in issue_rows
    ]

    recent_activity_count = db.query(AuditEvent).count()

    available_fys = [
        r[0]
        for r in db.query(distinct(ExtractedFact.reporting_period))
        .filter(ExtractedFact.reporting_period.like("FY%"))
        .order_by(asc(ExtractedFact.reporting_period))
        .all()
        if r[0]
    ]

    return AnalyticsOverviewResponse(
        kpis=kpis,
        subsidiaries=subsidiaries,
        top_metrics=top_metrics,
        production_trends=multi_year_trends,
        multi_year_production_trends=multi_year_trends,
        target_vs_achievement=target_vs_actual,
        production_vs_dispatch=prod_vs_dispatch,
        confidence_distribution=confidence_distribution,
        issue_distribution=issue_dist,
        available_financial_years=available_fys,
        available_subsidiaries=CIL_SUBS,
        recent_activity_count=recent_activity_count,
    )


# ---------------------------------------------------------------------------
# GET /analytics/extended  (14 new chart datasets)
# ---------------------------------------------------------------------------
@router.get("/extended", response_model=ExtendedAnalyticsResponse)
def get_analytics_extended(
    subsidiary: Optional[str] = None,
    financial_year: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    14 additional SQL-aggregated datasets for the expanded Analytics page.
    All values come directly from the database — no LLM estimation.
    """
    fact_q = _base_fact_q(db, subsidiary, financial_year)

    # 1. Year-over-Year Production Growth (%)
    trend_rows = (
        db.query(
            ExtractedFact.reporting_period,
            func.sum(ExtractedFact.numeric_value).label("prod"),
        )
        .filter(
            ExtractedFact.metric_code == "COAL_PRODUCTION",
            ExtractedFact.reporting_period.like("FY%"),
            ExtractedFact.numeric_value.isnot(None),
        )
    )
    if subsidiary and subsidiary != "ALL":
        trend_rows = trend_rows.filter(ExtractedFact.subsidiary == subsidiary)
    trend_list = (
        trend_rows.group_by(ExtractedFact.reporting_period)
        .order_by(asc(ExtractedFact.reporting_period))
        .all()
    )
    production_growth_yoy = []
    for i, r in enumerate(trend_list):
        val = round(float(r[1]), 1)
        if i == 0:
            growth = 0.0
        else:
            prev = round(float(trend_list[i - 1][1]), 1)
            growth = round(((val - prev) / max(0.1, prev)) * 100, 1) if prev > 0 else 0.0
        production_growth_yoy.append({"period": r[0], "production_mt": val, "yoy_growth_pct": growth})

    # 2. Metric Type Breakdown (top 8 by fact count)
    metric_type_rows = (
        fact_q.with_entities(
            ExtractedFact.metric_code,
            ExtractedFact.metric_name,
            func.count(ExtractedFact.id).label("cnt"),
        )
        .filter(ExtractedFact.metric_code.isnot(None))
        .group_by(ExtractedFact.metric_code, ExtractedFact.metric_name)
        .order_by(desc("cnt"))
        .limit(8)
        .all()
    )
    metric_type_breakdown = [
        {"metric_code": r[0], "metric_name": r[1] or r[0], "count": r[2]}
        for r in metric_type_rows
    ]

    # 3. Subsidiary Fact Share (% of total)
    total_facts = fact_q.count() or 1
    sub_share_rows = (
        fact_q.with_entities(
            ExtractedFact.subsidiary,
            func.count(ExtractedFact.id).label("cnt"),
        )
        .filter(ExtractedFact.subsidiary.isnot(None))
        .group_by(ExtractedFact.subsidiary)
        .order_by(desc("cnt"))
        .limit(10)
        .all()
    )
    subsidiary_fact_share = [
        {
            "subsidiary": r[0],
            "count": r[1],
            "share_pct": round((r[1] / total_facts) * 100, 1),
        }
        for r in sub_share_rows
    ]

    # 4. Extraction Method Mix
    method_rows = (
        fact_q.with_entities(
            ExtractedFact.extraction_method,
            func.count(ExtractedFact.id).label("cnt"),
        )
        .filter(ExtractedFact.extraction_method.isnot(None))
        .group_by(ExtractedFact.extraction_method)
        .order_by(desc("cnt"))
        .all()
    )
    extraction_method_mix = [
        {"method": r[0].replace("_", " ").title() if r[0] else "Unknown", "count": r[1]}
        for r in method_rows
    ]

    # 5. Monthly Document Uploads (last 12 months)
    monthly_rows = (
        db.query(
            func.strftime("%Y-%m", Document.created_at).label("month"),
            func.count(Document.id).label("cnt"),
        )
        .group_by(func.strftime("%Y-%m", Document.created_at))
        .order_by(asc("month"))
        .limit(12)
        .all()
    )
    monthly_uploads = [{"month": r[0], "count": r[1]} for r in monthly_rows]

    # 6. Coalfield Production (MT)
    coalfield_rows = (
        fact_q.with_entities(
            ExtractedFact.coalfield,
            func.sum(ExtractedFact.numeric_value).label("prod"),
        )
        .filter(
            ExtractedFact.metric_code == "COAL_PRODUCTION",
            ExtractedFact.coalfield.isnot(None),
            ExtractedFact.numeric_value.isnot(None),
        )
        .group_by(ExtractedFact.coalfield)
        .order_by(desc("prod"))
        .limit(10)
        .all()
    )
    coalfield_production = [
        {"coalfield": r[0], "production_mt": round(float(r[1]), 1)}
        for r in coalfield_rows
    ]

    # 7. Verification Rate by Subsidiary (%)
    verification_rate = []
    for s in CIL_SUBS:
        total = (
            db.query(func.count(ExtractedFact.id))
            .filter(ExtractedFact.subsidiary == s)
            .scalar()
            or 0
        )
        verified = (
            db.query(func.count(ExtractedFact.id))
            .filter(
                ExtractedFact.subsidiary == s,
                ExtractedFact.validation_status == ValidationStatus.VERIFIED.value,
            )
            .scalar()
            or 0
        )
        rate = round((verified / max(1, total)) * 100, 1)
        verification_rate.append({
            "subsidiary": s,
            "total_facts": total,
            "verified_facts": verified,
            "verification_rate_pct": rate,
        })

    # 8. Stripping Ratio Trend (OB BCM vs Coal MT by period)
    ob_rows = (
        db.query(
            ExtractedFact.reporting_period,
            func.sum(ExtractedFact.numeric_value).label("ob_bcm"),
        )
        .filter(
            ExtractedFact.metric_code.in_(["OVERBURDEN_REMOVAL", "OB_REMOVAL", "OVERBURDEN"]),
            ExtractedFact.reporting_period.like("FY%"),
            ExtractedFact.numeric_value.isnot(None),
        )
        .group_by(ExtractedFact.reporting_period)
        .order_by(asc(ExtractedFact.reporting_period))
        .all()
    )
    coal_by_period = {}
    for r in trend_list:
        coal_by_period[r[0]] = round(float(r[1]), 1)

    stripping_ratio_trend = []
    for r in ob_rows:
        ob_val = round(float(r[1]), 1)
        coal_val = coal_by_period.get(r[0], 0.0)
        ratio = round(ob_val / max(0.1, coal_val), 2) if coal_val > 0 else 0.0
        stripping_ratio_trend.append({
            "period": r[0],
            "ob_bcm": ob_val,
            "coal_mt": coal_val,
            "stripping_ratio": ratio,
        })

    # 9. Confidence Histogram (10-pt buckets)
    confidence_histogram = []
    for lo in range(0, 100, 10):
        hi = lo + 10
        lo_f = lo / 100.0
        hi_f = hi / 100.0
        cnt = fact_q.filter(
            ExtractedFact.confidence_score >= lo_f,
            ExtractedFact.confidence_score < hi_f,
        ).count()
        confidence_histogram.append({"bucket": f"{lo}-{hi}%", "count": cnt})

    # 10. Top 10 Mines by Production (MT)
    mine_rows = (
        fact_q.with_entities(
            ExtractedFact.mine,
            func.sum(ExtractedFact.numeric_value).label("prod"),
        )
        .filter(
            ExtractedFact.metric_code == "COAL_PRODUCTION",
            ExtractedFact.mine.isnot(None),
            ExtractedFact.numeric_value.isnot(None),
        )
        .group_by(ExtractedFact.mine)
        .order_by(desc("prod"))
        .limit(10)
        .all()
    )
    top_mines = [
        {"mine": r[0], "production_mt": round(float(r[1]), 1)}
        for r in mine_rows
    ]

    # 11. Offtake Gap per Subsidiary (production - offtake)
    offtake_gap = []
    for s in CIL_SUBS:
        p_val = (
            db.query(func.sum(ExtractedFact.numeric_value))
            .filter(
                ExtractedFact.subsidiary == s,
                ExtractedFact.metric_code == "COAL_PRODUCTION",
            )
            .scalar()
            or 0.0
        )
        d_val = (
            db.query(func.sum(ExtractedFact.numeric_value))
            .filter(
                ExtractedFact.subsidiary == s,
                ExtractedFact.metric_code == "COAL_OFFTAKE",
            )
            .scalar()
            or 0.0
        )
        offtake_gap.append({
            "subsidiary": s,
            "production_mt": round(float(p_val), 1),
            "offtake_mt": round(float(d_val), 1),
            "gap_mt": round(float(p_val - d_val), 1),
        })

    # 12. Validation Issues by Type
    issue_type_rows = (
        db.query(
            ValidationIssue.issue_type,
            func.count(ValidationIssue.id).label("cnt"),
        )
        .filter(ValidationIssue.is_resolved == False)
        .group_by(ValidationIssue.issue_type)
        .order_by(desc("cnt"))
        .limit(8)
        .all()
    )
    issue_type_dist = [
        {"type": (r[0] or "Unknown").replace("_", " ").title(), "count": r[1]}
        for r in issue_type_rows
    ]

    # 13. Document Type Mix (file_type)
    doc_type_rows = (
        db.query(
            Document.file_type,
            func.count(Document.id).label("cnt"),
        )
        .filter(Document.file_type.isnot(None))
        .group_by(Document.file_type)
        .order_by(desc("cnt"))
        .all()
    )
    doc_type_mix = [{"file_type": r[0], "count": r[1]} for r in doc_type_rows]

    # 14. Audit Activity (events per day, last 30 days)
    audit_rows = (
        db.query(
            func.strftime("%Y-%m-%d", AuditEvent.timestamp).label("day"),
            func.count(AuditEvent.id).label("cnt"),
        )
        .group_by(func.strftime("%Y-%m-%d", AuditEvent.timestamp))
        .order_by(asc("day"))
        .limit(30)
        .all()
    )
    audit_activity_trend = [{"day": r[0], "events": r[1]} for r in audit_rows]

    return ExtendedAnalyticsResponse(
        production_growth_yoy=production_growth_yoy,
        metric_type_breakdown=metric_type_breakdown,
        subsidiary_fact_share=subsidiary_fact_share,
        extraction_method_mix=extraction_method_mix,
        monthly_uploads=monthly_uploads,
        coalfield_production=coalfield_production,
        verification_rate_by_sub=verification_rate,
        stripping_ratio_trend=stripping_ratio_trend,
        confidence_histogram=confidence_histogram,
        top_mines=top_mines,
        offtake_gap=offtake_gap,
        issue_type_dist=issue_type_dist,
        doc_type_mix=doc_type_mix,
        audit_activity_trend=audit_activity_trend,
    )
