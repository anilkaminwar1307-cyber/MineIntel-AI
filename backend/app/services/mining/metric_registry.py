"""
MiningMetricRegistry — Canonical metric codes and alias → code mappings.
All alias matching is case-insensitive and deterministic. Zero LLM hallucination.

CANONICAL CODES:
  COAL_OFFTAKE       — dispatch/offtake (was COAL_DISPATCH in registry v1; DB always used COAL_OFFTAKE)
  GEOLOGICAL_RESERVES — geological reserves (was GEOLOGICAL_RESERVE singular in registry v1)

  All legacy aliases (COAL_DISPATCH, GEOLOGICAL_RESERVE) map to the canonical codes above
  so existing queries and tests continue to resolve correctly.
"""
from typing import Optional, Dict, List, Tuple

# (metric_code, canonical_name, default_unit)
# ⚠️  metric_code MUST match the value stored in extracted_facts.metric_code in the database.
METRIC_DEFINITIONS: List[Tuple[str, str, str]] = [
    ("COAL_PRODUCTION",              "Coal Production",                  "MT"),
    ("PRODUCTION_TARGET",            "Production Target",                "MT"),
    # Canonical: COAL_OFFTAKE (DB has 5,376 facts under this code)
    ("COAL_OFFTAKE",                 "Coal Dispatch / Offtake",          "MT"),
    ("DISPATCH_TARGET",              "Dispatch Target",                  "MT"),
    # Canonical: GEOLOGICAL_RESERVES (DB has 4,301 facts under this code)
    ("GEOLOGICAL_RESERVES",          "Geological Reserves",              "MT"),
    ("PROVED_RESERVE",               "Proved Reserve",                   "MT"),
    ("INDICATED_RESERVE",            "Indicated Reserve",                "MT"),
    ("INFERRED_RESERVE",             "Inferred Reserve",                 "MT"),
    ("OVERBURDEN_REMOVAL",           "Overburden Removal",               "Mm3"),
    ("OB_TARGET",                    "Overburden Target",                "Mm3"),
    ("DRILLING",                     "Drilling",                         "m"),
    ("EXPLORATION_BOREHOLES",        "Exploration Boreholes",            "count"),
    ("BOREHOLE_COUNT",               "Boreholes Drilled",                "count"),
    ("EXPLORATION_AREA",             "Exploration Area",                 "sq km"),
    ("COAL_STOCK",                   "Coal Stock",                       "MT"),
    ("MINE_AREA",                    "Mine Area",                        "ha"),
    ("STRIPPING_RATIO",              "Stripping Ratio",                  "m3/t"),
    ("TARGET_ACHIEVEMENT",           "Target Achievement",               "%"),
    ("CAPITAL_EXPENDITURE",          "Capital Expenditure",              "INR Cr"),
    ("MANPOWER",                     "Manpower",                         "count"),
    ("ENVIRONMENTAL_CLEARANCE_AREA", "Environmental Clearance Area",     "ha"),
    ("ENVIRONMENTAL_CLEARANCE",      "Environmental Clearance Area",     "ha"),
    ("WASHERY_CAPACITY",             "Washery Capacity",                 "MTPA"),
    ("COAL_QUALITY",                 "Coal Quality",                     "kcal/kg"),
    ("GCV_QUALITY",                  "Coal Quality (GCV)",               "kcal/kg"),
    ("COAL_QUALITY_GCV",             "Coal Quality (GCV)",               "kcal/kg"),
    ("COAL_QUALITY_ASH",             "Coal Quality (Ash)",               "%"),
    ("WASHED_COAL_YIELD",            "Washed Coal Yield",                "%"),
    ("SEAM_THICKNESS",               "Seam Thickness",                   "m"),
    ("DEPTH",                        "Depth",                            "m"),
    ("REVENUE",                      "Revenue",                          "INR Cr"),
    ("PROFIT",                       "Profit / Loss",                    "INR Cr"),
    ("ROYALTY",                      "Royalty",                          "INR Cr"),
    ("SPECIFIC_POWER_CONSUMPTION",   "Specific Power Consumption",       "kWh/t"),
]

# ─── Legacy/alias code → canonical code ───────────────────────────────────────
# Maps old or alternative metric codes to the canonical code stored in the DB.
LEGACY_CODE_MAP: Dict[str, str] = {
    "COAL_DISPATCH":    "COAL_OFFTAKE",       # Registry v1 used COAL_DISPATCH
    "GEOLOGICAL_RESERVE": "GEOLOGICAL_RESERVES",  # Registry v1 used singular
    "COAL_QUALITY_GCV": "GCV_QUALITY",        # DB uses GCV_QUALITY
}


def resolve_legacy_code(code: str) -> str:
    """Resolve a potentially-legacy metric code to its canonical DB code."""
    return LEGACY_CODE_MAP.get(code, code)


# ─── alias text → canonical metric_code ───────────────────────────────────────
# All alias keys must be lowercase.
METRIC_ALIASES: Dict[str, str] = {
    # Coal Production
    "coal production":      "COAL_PRODUCTION",
    "actual production":    "COAL_PRODUCTION",
    "production":           "COAL_PRODUCTION",
    "raw coal production":  "COAL_PRODUCTION",
    "coal output":          "COAL_PRODUCTION",
    "output":               "COAL_PRODUCTION",
    "coal extraction":      "COAL_PRODUCTION",
    "extraction":           "COAL_PRODUCTION",
    "coal raised":          "COAL_PRODUCTION",

    # Production Target
    "production target":    "PRODUCTION_TARGET",
    "target production":    "PRODUCTION_TARGET",
    "planned production":   "PRODUCTION_TARGET",
    "target":               "PRODUCTION_TARGET",
    "annual target":        "PRODUCTION_TARGET",

    # Coal Dispatch / Offtake — canonical: COAL_OFFTAKE
    "coal dispatch":        "COAL_OFFTAKE",
    "dispatch":             "COAL_OFFTAKE",
    "offtake":              "COAL_OFFTAKE",
    "coal offtake":         "COAL_OFFTAKE",
    "despatches":           "COAL_OFFTAKE",
    "dispatches":           "COAL_OFFTAKE",
    "coal despatches":      "COAL_OFFTAKE",

    # Dispatch Target
    "dispatch target":      "DISPATCH_TARGET",
    "target dispatch":      "DISPATCH_TARGET",
    "planned dispatch":     "DISPATCH_TARGET",

    # Geological Reserves — canonical: GEOLOGICAL_RESERVES (plural)
    "geological reserve":   "GEOLOGICAL_RESERVES",
    "geological reserves":  "GEOLOGICAL_RESERVES",
    "coal reserve":         "GEOLOGICAL_RESERVES",
    "coal reserves":        "GEOLOGICAL_RESERVES",
    "coal resource":        "GEOLOGICAL_RESERVES",
    "resources":            "GEOLOGICAL_RESERVES",
    "total reserve":        "GEOLOGICAL_RESERVES",
    "proved reserve":       "PROVED_RESERVE",
    "proved reserves":      "PROVED_RESERVE",
    "indicated reserve":    "INDICATED_RESERVE",
    "inferred reserve":     "INFERRED_RESERVE",

    # Overburden
    "overburden":               "OVERBURDEN_REMOVAL",
    "overburden removal":       "OVERBURDEN_REMOVAL",
    "ob removal":               "OVERBURDEN_REMOVAL",
    "ob":                       "OVERBURDEN_REMOVAL",
    "o/b":                      "OVERBURDEN_REMOVAL",
    "overburden excavation":    "OVERBURDEN_REMOVAL",
    "waste removal":            "OVERBURDEN_REMOVAL",
    "ob target":                "OB_TARGET",
    "overburden target":        "OB_TARGET",

    # Drilling & Boreholes
    "drilling":                 "DRILLING",
    "drilled metres":           "DRILLING",
    "drilled meters":           "DRILLING",
    "meterage":                 "DRILLING",
    "core drilling":            "DRILLING",
    "total drilling":           "DRILLING",
    "drilling meterage":        "DRILLING",
    "exploration boreholes":    "EXPLORATION_BOREHOLES",
    "boreholes":                "EXPLORATION_BOREHOLES",
    "boreholes drilled":        "EXPLORATION_BOREHOLES",
    "number of boreholes":      "EXPLORATION_BOREHOLES",

    # Coal Stock
    "coal stock":               "COAL_STOCK",
    "stock":                    "COAL_STOCK",
    "pit head stock":           "COAL_STOCK",
    "closing stock":            "COAL_STOCK",

    # Mine Area
    "mine area":                "MINE_AREA",
    "leasehold area":           "MINE_AREA",
    "total area":               "MINE_AREA",

    # Stripping Ratio
    "stripping ratio":          "STRIPPING_RATIO",
    "sr":                       "STRIPPING_RATIO",
    "s/r":                      "STRIPPING_RATIO",

    # Target Achievement
    "target achievement":       "TARGET_ACHIEVEMENT",
    "achievement":              "TARGET_ACHIEVEMENT",
    "% achievement":            "TARGET_ACHIEVEMENT",
    "achievement %":            "TARGET_ACHIEVEMENT",

    # Financial & Capex
    "capex":                    "CAPITAL_EXPENDITURE",
    "capital expenditure":      "CAPITAL_EXPENDITURE",
    "revenue":                  "REVENUE",
    "turnover":                 "REVENUE",
    "profit":                   "PROFIT",
    "loss":                     "PROFIT",
    "royalty":                  "ROYALTY",

    # Manpower
    "manpower":                 "MANPOWER",
    "employees":                "MANPOWER",
    "workforce":                "MANPOWER",
    "total manpower":           "MANPOWER",

    # Environmental Clearance
    "environmental clearance area": "ENVIRONMENTAL_CLEARANCE_AREA",
    "environmental clearance":      "ENVIRONMENTAL_CLEARANCE",
    "forest clearance":             "ENVIRONMENTAL_CLEARANCE_AREA",
    "ec area":                      "ENVIRONMENTAL_CLEARANCE_AREA",

    # Washery
    "washery capacity":             "WASHERY_CAPACITY",
    "coal washery":                 "WASHERY_CAPACITY",

    # Quality & Seam
    "coal quality":                 "COAL_QUALITY",
    "gcv":                          "GCV_QUALITY",
    "gross calorific value":        "GCV_QUALITY",
    "ash":                          "COAL_QUALITY_ASH",
    "seam thickness":               "SEAM_THICKNESS",
    "thickness":                    "SEAM_THICKNESS",
    "depth":                        "DEPTH",
    "mine depth":                   "DEPTH",
    "washed coal yield":            "WASHED_COAL_YIELD",
    "specific power consumption":   "SPECIFIC_POWER_CONSUMPTION",
    "spc":                          "SPECIFIC_POWER_CONSUMPTION",
}

_CODE_TO_NAME: Dict[str, str] = {code: name for code, name, _ in METRIC_DEFINITIONS}
_CODE_TO_UNIT: Dict[str, str] = {code: unit for code, _, unit in METRIC_DEFINITIONS}


class MiningMetricRegistry:
    def resolve(self, raw_text: str) -> Optional[Tuple[str, str, str]]:
        if not raw_text:
            return None
        normalized = raw_text.strip().lower()

        # Direct alias lookup
        if normalized in METRIC_ALIASES:
            code = METRIC_ALIASES[normalized]
            return code, _CODE_TO_NAME.get(code, code), _CODE_TO_UNIT.get(code, "")

        # Clean punctuation and check
        clean_text = normalized.replace("_", " ").replace("-", " ")
        if clean_text in METRIC_ALIASES:
            code = METRIC_ALIASES[clean_text]
            return code, _CODE_TO_NAME.get(code, code), _CODE_TO_UNIT.get(code, "")

        # Substring alias scan (longest match first)
        best_match = None
        best_len = 0
        for alias, code in METRIC_ALIASES.items():
            if alias in normalized and len(alias) > best_len:
                best_match = code
                best_len = len(alias)

        if best_match:
            return best_match, _CODE_TO_NAME.get(best_match, best_match), _CODE_TO_UNIT.get(best_match, "")

        return None

    @classmethod
    def find_metric(cls, raw_text: str) -> Optional[Dict[str, str]]:
        if not raw_text:
            return None
        res = cls().resolve(raw_text)
        if res:
            return {"code": res[0], "name": res[1], "default_unit": res[2]}
        return None

    def get_canonical_name(self, metric_code: str) -> str:
        canonical = resolve_legacy_code(metric_code)
        return _CODE_TO_NAME.get(canonical, metric_code)

    def get_default_unit(self, metric_code: str) -> str:
        canonical = resolve_legacy_code(metric_code)
        return _CODE_TO_UNIT.get(canonical, "")

    def all_codes(self) -> List[str]:
        return list(_CODE_TO_NAME.keys())


metric_registry = MiningMetricRegistry()
