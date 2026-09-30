"""
NumberSafe 2.0 — Duplicate Detector
Identifies facts that represent the same real-world observation so they
are not counted twice in aggregations.

Detection strategies:
  1. EXACT DUPLICATE — identical (subsidiary, metric_code, reporting_period,
     mine, numeric_value) — keep the one with highest confidence / verified status.
  2. ANNUAL + COMPONENT OVERLAP — an annual row and monthly component rows for
     the same entity+period — exclude the component rows when annual is present
     (or vice-versa depending on preference setting).
  3. CONSOLIDATED + SUBSIDIARY OVERLAP — a CIL-total row and subsidiary rows —
     exclude consolidated when subsidiaries are available.
"""
from __future__ import annotations
import re
from typing import List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class FactCandidate:
    """Lightweight representation of a fact for duplicate analysis."""
    fact_id: str
    metric_code: str
    subsidiary: Optional[str]
    mine: Optional[str]
    reporting_period: Optional[str]
    numeric_value: Optional[float]
    validation_status: str
    confidence_score: float
    is_demo: bool
    extraction_method: str
    temporal_grain: Optional[str] = None   # ANNUAL / MONTHLY / QUARTERLY / etc.
    document_id: Optional[str] = None


@dataclass
class ExclusionDecision:
    fact_id: str
    reason: str
    excluded_in_favour_of: Optional[str] = None   # fact_id that was kept


def detect_duplicates(
    candidates: List[FactCandidate],
    prefer_verified: bool = True,
    exclude_consolidated: bool = True,
) -> Tuple[List[str], List[ExclusionDecision]]:
    """
    Analyses a list of fact candidates and returns:
      - included_ids: list of fact IDs that should be used in aggregation
      - exclusions: list of ExclusionDecision explaining what was dropped

    Strategy applied in order:
      1. Exact duplicate by (subsidiary, metric, period, mine, value) →
         keep highest-confidence / verified.
      2. Consolidated CIL + component subsidiaries overlap →
         exclude consolidated row.
      3. Annual + monthly component overlap for same entity →
         exclude monthly component rows.
    """
    included_ids: List[str] = []
    exclusions: List[ExclusionDecision] = []

    # Group by dedup key
    seen: dict[tuple, FactCandidate] = {}
    late_exclusions: List[ExclusionDecision] = []

    for fc in candidates:
        norm_period = _normalize_period(fc.reporting_period)
        key = (
            (fc.subsidiary or "").upper(),
            fc.metric_code,
            norm_period,
            (fc.mine or "").upper(),
            _round_val(fc.numeric_value),
        )
        if key in seen:
            existing = seen[key]
            # Keep verified over unverified; otherwise keep higher confidence
            if _prefer(fc, existing, prefer_verified):
                # New is better → exclude existing
                late_exclusions.append(ExclusionDecision(
                    fact_id=existing.fact_id,
                    reason="EXACT_DUPLICATE — lower confidence/verification than another record with identical (subsidiary, metric, period, mine, value)",
                    excluded_in_favour_of=fc.fact_id,
                ))
                seen[key] = fc
            else:
                # Existing is better → exclude new
                late_exclusions.append(ExclusionDecision(
                    fact_id=fc.fact_id,
                    reason="EXACT_DUPLICATE — lower confidence/verification than another record with identical (subsidiary, metric, period, mine, value)",
                    excluded_in_favour_of=existing.fact_id,
                ))
        else:
            seen[key] = fc

    # Consolidated vs subsidiary overlap
    # If we have subsidiary-level rows, drop CIL/consolidated rows
    if exclude_consolidated:
        consolidated_ids = {
            fc.fact_id
            for fc in candidates
            if (fc.subsidiary or "").upper() in ("CIL", "COAL INDIA", "CONSOLIDATED")
        }
        subsidiary_present = any(
            (fc.subsidiary or "").upper() not in ("CIL", "COAL INDIA", "CONSOLIDATED", "")
            for fc in candidates
        )
        if consolidated_ids and subsidiary_present:
            for fid in consolidated_ids:
                if fid in {k.fact_id for k in seen.values()}:
                    late_exclusions.append(ExclusionDecision(
                        fact_id=fid,
                        reason="CONSOLIDATED_OVERLAP — CIL/consolidated row excluded because subsidiary-level rows are present; summing both would double-count",
                    ))
                    # Remove from seen dict
                    seen = {k: v for k, v in seen.items() if v.fact_id != fid}

    # Temporal overlap: annual + monthly components for same entity+metric
    # If an ANNUAL grain row exists, exclude MONTHLY rows for the same entity+year
    annual_keys: set[tuple] = set()
    for fc in seen.values():
        grain = _infer_temporal_grain(fc)
        if grain == "ANNUAL":
            period_year = _extract_fy_year(fc.reporting_period or "")
            annual_keys.add((
                (fc.subsidiary or "").upper(),
                fc.metric_code,
                period_year,
                (fc.mine or "").upper(),
            ))

    if annual_keys:
        to_remove: List[str] = []
        for fc in list(seen.values()):
            grain = _infer_temporal_grain(fc)
            if grain in ("MONTHLY", "QUARTERLY"):
                period_year = _extract_fy_year(fc.reporting_period or "")
                overlap_key = (
                    (fc.subsidiary or "").upper(),
                    fc.metric_code,
                    period_year,
                    (fc.mine or "").upper(),
                )
                if overlap_key in annual_keys:
                    late_exclusions.append(ExclusionDecision(
                        fact_id=fc.fact_id,
                        reason=f"TEMPORAL_OVERLAP — {grain} component excluded because an ANNUAL row for the same entity+period is present; summing both would double-count",
                    ))
                    to_remove.append(fc.fact_id)
        seen = {k: v for k, v in seen.items() if v.fact_id not in to_remove}

    excluded_ids = {ex.fact_id for ex in late_exclusions}
    included_ids = [fc.fact_id for fc in seen.values() if fc.fact_id not in excluded_ids]
    exclusions = late_exclusions

    return included_ids, exclusions


def _prefer(new: FactCandidate, existing: FactCandidate, prefer_verified: bool) -> bool:
    """Returns True if `new` should replace `existing`."""
    if prefer_verified:
        new_verified = new.validation_status.upper() == "VERIFIED"
        existing_verified = existing.validation_status.upper() == "VERIFIED"
        if new_verified and not existing_verified:
            return True
        if existing_verified and not new_verified:
            return False
    return new.confidence_score > existing.confidence_score


def _round_val(v: Optional[float]) -> Optional[float]:
    if v is None:
        return None
    return round(v, 3)


def _normalize_period(period: Optional[str]) -> str:
    """Normalizes period strings like 'FY 2024-25', 'FY24-25', '2024-25' into a canonical form."""
    if not period:
        return ""
    import re
    cleaned = period.strip().upper().replace("–", "-")
    # If it has a standard FY pattern e.g. FY 2024-25 or 2024-25
    m = re.search(r'(?:FY\s*)?(20\d{2})[-/](\d{2,4})', cleaned)
    if m:
        y1 = m.group(1)
        y2 = m.group(2)
        if len(y2) == 4:
            y2 = y2[2:]
        return f"FY {y1}-{y2}"
    return cleaned


def _infer_temporal_grain(fc: FactCandidate) -> str:
    """Infers temporal grain if not explicitly specified."""
    if fc.temporal_grain:
        return fc.temporal_grain.upper()
    if not fc.reporting_period:
        return "ANY"
    
    p = fc.reporting_period.upper()
    if any(q in p for q in ["Q1", "Q2", "Q3", "Q4", "QUARTER"]):
        return "QUARTERLY"
    months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    if any(m in p for m in months) or "-01" in p or "-02" in p or "-03" in p or "-04" in p or "-05" in p or "-06" in p:
        return "MONTHLY"
    if "FY" in p or "ANNUAL" in p or re.search(r'20\d{2}-\d{2}', p):
        return "ANNUAL"
    return "ANY"


def _extract_fy_year(period: str) -> str:
    """Extracts the financial year key (e.g. '2024-25') from a period string."""
    if not period:
        return ""
    # Standard FY pattern: e.g. FY 2024-25 or 2024-25
    m = re.search(r'20(\d{2})[-–](\d{2,4})', period)
    if m:
        y1 = m.group(1)
        y2 = m.group(2)
        if len(y2) == 4:
            y2 = y2[2:]
        return f"20{y1}-{y2}"

    # Check for Month-Year or Year-Month (e.g. Apr-2024, 2024-04, April 2024)
    # In Indian FY (April to March):
    # Apr-Dec of year Y belongs to FY Y-(Y+1)
    # Jan-Mar of year Y belongs to FY (Y-1)-Y
    MONTH_MAP = {
        "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
        "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12
    }
    p_upper = period.upper()
    year_match = re.search(r'(20\d{2})', period)
    if year_match:
        yr = int(year_match.group(1))
        month_num = None
        for m_str, m_val in MONTH_MAP.items():
            if m_str in p_upper:
                month_num = m_val
                break
        if month_num is None:
            # Check numeric month: e.g. 2024-04 or 04-2024
            num_m = re.search(r'(?:^|[^\d])(0?[1-9]|1[0-2])(?:[^\d]|$)', period)
            if num_m and num_m.group(1) != year_match.group(1):
                month_num = int(num_m.group(1))

        if month_num is not None:
            if month_num >= 4:
                fy_start = yr
                fy_end = (yr + 1) % 100
            else:
                fy_start = yr - 1
                fy_end = yr % 100
            return f"{fy_start}-{fy_end:02d}"

    m = re.search(r'(FY\s*\d{4}-\d{2,4})', period, re.IGNORECASE)
    if m:
        return m.group(1).upper().replace(" ", "")
    return period.upper()
