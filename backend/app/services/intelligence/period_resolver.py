"""
Time and Period Resolver for Ask MineIntel.
Normalizes Indian financial year, quarterly, monthly, and calendar date expressions
into canonical representations (e.g. 'FY 2024-25').
"""
import re
from typing import Optional, Dict, Any, Tuple
from app.services.mining.period_normalizer import PeriodNormalizer, normalize_period


class MiningPeriodResolver:
    """Extracts and standardizes reporting periods from mining queries."""

    @classmethod
    def resolve_period(cls, query_text: str) -> Dict[str, Any]:
        """
        Returns:
        - period: Canonical string (e.g., 'FY 2024-25', 'Q3 FY 2024-25') or None
        - raw_match: Matched substring
        - period_type: 'ANNUAL_FY', 'QUARTER_FY', 'MONTHLY', 'CALENDAR_YEAR', or None
        - is_ambiguous: True if multiple conflicting years/periods are detected
        """
        text = (query_text or "").strip()
        result: Dict[str, Any] = {
            "period": None,
            "raw_match": None,
            "period_type": None,
            "is_ambiguous": False,
        }
        if not text:
            return result

        # First, try PeriodNormalizer
        extracted = PeriodNormalizer.extract_period(text)
        if extracted:
            canonical = normalize_period(extracted)
            result["period"] = canonical
            result["raw_match"] = extracted

            if "Q" in canonical:
                result["period_type"] = "QUARTER_FY"
            elif canonical.startswith("FY"):
                result["period_type"] = "ANNUAL_FY"
            else:
                result["period_type"] = "OTHER"
            return result

        # Custom quarterly pattern: Q1/Q2/Q3/Q4 of FY25, Q3 2024-25
        qm = re.search(r"\b(Q[1-4])\s*(?:of\s*)?(?:FY\s*)?(\d{2,4})(?:[-/](\d{2,4}))?\b", text, re.IGNORECASE)
        if qm:
            quarter = qm.group(1).upper()
            y1 = qm.group(2)
            y2 = qm.group(3)
            if y2:
                fy_str = f"{quarter} FY {y1 if len(y1) == 4 else '20' + y1}-{y2 if len(y2) == 2 else y2[-2:]}"
            else:
                fy_str = f"{quarter} FY {y1}"
            result["period"] = fy_str
            result["raw_match"] = qm.group(0)
            result["period_type"] = "QUARTER_FY"
            return result

        # Fallback to direct normalize_period on the text
        canon = normalize_period(text)
        if canon:
            result["period"] = canon
            result["raw_match"] = canon
            result["period_type"] = "ANNUAL_FY"
            return result

        return result
