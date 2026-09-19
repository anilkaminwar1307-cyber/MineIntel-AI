"""
Unit normalizer — maps raw unit strings to canonical unit codes.
Deterministic regex + lookup. No LLM involved.
"""
import re
from typing import Optional, Tuple

# (raw_patterns, canonical_unit)
UNIT_PATTERNS = [
    # Million Tonnes
    (r"\b(m\.?t\.?|million\s+t(?:onne)?s?|mt)\b", "MT"),
    # MTPA
    (r"\b(mtpa|mt\s*/\s*(?:year|yr|annum|pa))\b", "MTPA"),
    # Thousand Tonnes / Tonnes
    (r"\b(thou(?:sand)?\s+t(?:onne)?s?|000\s*t)\b", "000T"),
    (r"\b(t(?:onne)?s?)\b", "T"),
    # Metres
    (r"\b(m(?:etres?|eters?)?)\b(?!\s*t)", "m"),   # 'm' alone (not 'mt')
    (r"\b(km|kilo\s*m(?:etres?|eters?)?)\b", "km"),
    # Cubic metres
    (r"\b(mm\s*3|million\s*m\s*3|mcm)\b", "Mm3"),
    (r"\b(m\s*3)\b", "m3"),
    # Hectares / sq km
    (r"\b(ha|hectares?)\b", "ha"),
    (r"\b(sq\.?\s*km|km\s*2)\b", "sq km"),
    # Percentage
    (r"(%|\bper\s*cent(?:age)?\b)", "%"),
    # Currency
    (r"(\binr\s*cr|₹\s*cr(?:ore)?|\brs\.?\s*cr(?:ore)?|\bcrore(?:s)?\b)", "INR Cr"),
    (r"(\binr\s*lakh|\brs\.?\s*lakh\b|₹\s*lakh)", "INR Lakh"),
    # Energy
    (r"\b(kcal\s*/\s*kg|kcal/kg)\b", "kcal/kg"),
    # Ratio
    (r"\b(m\s*3\s*/\s*t|m3/t|bcm/t)\b", "m3/t"),
    # Count
    (r"\b(nos?\.?|numbers?|count)\b", "count"),
    # BCM
    (r"\b(bcm|billion\s*cubic\s*metres?)\b", "BCM"),
]

COMPILED_PATTERNS = [(re.compile(pat, re.IGNORECASE), canon) for pat, canon in UNIT_PATTERNS]


class UnitNormalizer:
    """
    Recognizes and normalizes mining units from raw text fragments.
    Returns (canonical_unit, raw_unit) or (raw, raw) if unrecognized.
    """

    @classmethod
    def normalize(cls, raw_unit: Optional[str]) -> Tuple[str, str]:
        if not raw_unit:
            return "", ""
        raw = raw_unit.strip()
        for pattern, canonical in COMPILED_PATTERNS:
            if pattern.search(raw):
                return canonical, raw
        return "", raw

    @classmethod
    def extract_from_text(cls, text: str) -> Optional[str]:
        for pattern, canonical in COMPILED_PATTERNS:
            if pattern.search(text):
                return canonical
        return None


unit_normalizer = UnitNormalizer()
