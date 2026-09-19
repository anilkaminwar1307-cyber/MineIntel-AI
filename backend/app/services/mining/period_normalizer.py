"""
Reporting period normalizer — converts various FY / date formats to canonical "FY YYYY-YY".
Deterministic regex only.
"""
import re
from typing import Optional, List


# Patterns — most specific first
PERIOD_PATTERNS = [
    # FY 2025-26 (already canonical)
    (re.compile(r"\bfy\s*(\d{4})-(\d{2,4})\b", re.IGNORECASE), "FY {y1}-{y2}"),
    # 2025-26 (bare range)
    (re.compile(r"\b(\d{4})-(\d{2})\b"), "FY {y1}-{y2}"),
    # 2025/26
    (re.compile(r"\b(\d{4})/(\d{2})\b"), "FY {y1}-{y2}"),
    # FY2026 (single year — infer FY 2025-26)
    (re.compile(r"\bfy(\d{4})\b", re.IGNORECASE), "FY {y0}-{y0s}"),
    # Financial Year 2025-26
    (re.compile(r"\bfinancial\s+year\s+(\d{4})-(\d{2,4})\b", re.IGNORECASE), "FY {y1}-{y2}"),
    # 2025-2026 (long form)
    (re.compile(r"\b(\d{4})-(\d{4})\b"), "FY {y1}-{y2long}"),
    # Quarter: Q1 FY 2025-26 / Q2 2025
    (re.compile(r"\b(q[1-4])\s+(?:fy\s*)?(\d{4})(?:-(\d{2,4}))?\b", re.IGNORECASE), "{quarter} FY {qy}"),
    # Month + Year: April 2025 / Apr 2025
    (re.compile(
        r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
        r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
        r"\s+(\d{4})\b", re.IGNORECASE
    ), "{month} {my}"),
    # YYYY alone (calendar year)
    (re.compile(r"\b(20\d{2})\b"), "CY {cy}"),
]


def _last_two(year: str) -> str:
    return year[-2:]


def normalize_period(raw: str) -> Optional[str]:
    """
    Convert raw period string to canonical form.
    Returns None if no period can be recognized.
    """
    if not raw:
        return None
    raw = raw.strip()

    # Q1/Q2/Q3/Q4 FY 2025-26
    m = re.search(r"\b(q[1-4])\s+(?:fy\s*)?(\d{4})(?:-(\d{2,4}))?\b", raw, re.IGNORECASE)
    if m:
        quarter = m.group(1).upper()
        year = m.group(2)
        suffix = f"-{_last_two(m.group(3))}" if m.group(3) else ""
        return f"{quarter} FY {year}{suffix}"

    # FY YYYY-YY already canonical
    m = re.match(r"\bFY\s+(\d{4})-(\d{2})\b", raw, re.IGNORECASE)
    if m:
        return f"FY {m.group(1)}-{m.group(2)}"

    # FY YYYY-YYYY → FY YYYY-YY
    m = re.search(r"\bfy\s*(\d{4})-(\d{4})\b", raw, re.IGNORECASE)
    if m:
        return f"FY {m.group(1)}-{_last_two(m.group(2))}"

    # FY YYYY-YY
    m = re.search(r"\bfy\s*(\d{4})-(\d{2})\b", raw, re.IGNORECASE)
    if m:
        return f"FY {m.group(1)}-{m.group(2)}"

    # 2025-26
    m = re.search(r"\b(\d{4})-(\d{2})\b", raw)
    if m and m.group(2).isdigit():
        return f"FY {m.group(1)}-{m.group(2)}"

    # 2025/26
    m = re.search(r"\b(\d{4})/(\d{2})\b", raw)
    if m:
        return f"FY {m.group(1)}-{m.group(2)}"

    # FY2026 → FY 2025-26
    m = re.search(r"\bfy(\d{4})\b", raw, re.IGNORECASE)
    if m:
        y = int(m.group(1))
        return f"FY {y-1}-{str(y)[-2:]}"

    # Financial Year 2025-26
    m = re.search(r"\bfinancial\s+year\s+(\d{4})-(\d{2,4})\b", raw, re.IGNORECASE)
    if m:
        return f"FY {m.group(1)}-{_last_two(m.group(2))}"

    # Q1/Q2/Q3/Q4 FY 2025-26
    m = re.search(r"\b(q[1-4])\s+(?:fy\s*)?(\d{4})(?:-(\d{2,4}))?\b", raw, re.IGNORECASE)
    if m:
        quarter = m.group(1).upper()
        year = m.group(2)
        suffix = f"-{_last_two(m.group(3))}" if m.group(3) else ""
        return f"{quarter} FY {year}{suffix}"

    # Month Year
    m = re.search(
        r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
        r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
        r"\s+(\d{4})\b",
        raw, re.IGNORECASE
    )
    if m:
        month = m.group(1).capitalize()[:3]
        year = m.group(2)
        return f"{month} {year}"

    return None


def extract_periods_from_text(text: str) -> List[str]:
    """Extract all recognizable period strings from a block of text."""
    results = []
    for pattern, _ in PERIOD_PATTERNS:
        for m in pattern.finditer(text):
            p = normalize_period(m.group(0))
            if p and p not in results:
                results.append(p)
    return results


class PeriodNormalizer:
    @staticmethod
    def normalize_period(raw: str) -> Optional[str]:
        return normalize_period(raw)

    @staticmethod
    def extract_period(text: str) -> Optional[str]:
        periods = extract_periods_from_text(text)
        return periods[0] if periods else None

    @staticmethod
    def extract_periods_from_text(text: str) -> List[str]:
        return extract_periods_from_text(text)
