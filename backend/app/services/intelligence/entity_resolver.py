"""
Mining Domain Entity & Metric Resolver.
Resolves acronyms, canonical metrics, subsidiaries, mines, and units without LLM hallucination.
"""
import re
from typing import Optional, Dict, Any, List, Tuple
from app.services.mining.org_normalizer import OrgNormalizer, VALID_SUBSIDIARIES, ORGANIZATION_MAP
from app.services.mining.metric_registry import metric_registry, METRIC_ALIASES, METRIC_DEFINITIONS


# Well-known flagship mines across CIL subsidiaries
KNOWN_FLAGSHIP_MINES: Dict[str, str] = {
    "gevra": "SECL",
    "kusmunda": "SECL",
    "dipka": "SECL",
    "jayant": "NCL",
    "dudhichua": "NCL",
    "nigahi": "NCL",
    "amlohri": "NCL",
    "bhubaneswari": "MCL",
    "samaleswari": "MCL",
    "lakhanpur": "MCL",
    "kulda": "MCL",
    "belpahar": "MCL",
    "rajmahal": "ECL",
    "sonepur bazari": "ECL",
    "piparwar": "CCL",
    "ashok": "CCL",
    "amrapali": "CCL",
    "magadh": "CCL",
    "moonidih": "BCCL",
    "katras": "BCCL",
    "kusunda": "BCCL",
    "umrer": "WCL",
}


class MiningEntityResolver:
    """Extracts and resolves canonical mining entities, metrics, and units from query strings."""

    @classmethod
    def resolve_entities(cls, query_text: str) -> Dict[str, Any]:
        """
        Extracts:
        - subsidiary: Canonical acronym (e.g. 'SECL') or None
        - subsidiaries: List of all matched subsidiaries
        - mine: Identified mine or colliery name
        - metric_code: Canonical DB metric code (e.g. 'COAL_PRODUCTION')
        - metric_name: Human readable metric title
        - unit: Canonical unit (e.g. 'MT', 'Mm3', 'm')
        - raw_matched_metric: Raw substring matched
        """
        text = (query_text or "").strip()
        lowered = text.lower()

        resolved: Dict[str, Any] = {
            "subsidiary": None,
            "subsidiaries": [],
            "mine": None,
            "metric_code": None,
            "metric_name": None,
            "unit": None,
            "raw_matched_metric": None,
            "is_all_subsidiaries": False,
        }

        # 1. Check for "all subsidiaries" / "across subsidiaries"
        if re.search(r"\b(?:all\s+subsidiaries|across\s+subsidiaries|each\s+subsidiary|subsidiary\s+wise)\b", lowered):
            resolved["is_all_subsidiaries"] = True

        # 2. Subsidiary Extraction
        found_subs = []
        for alias, (code, full_name) in ORGANIZATION_MAP.items():
            pattern = rf"\b{re.escape(alias)}\b"
            if re.search(pattern, lowered):
                if code not in found_subs:
                    found_subs.append(code)

        for code in VALID_SUBSIDIARIES:
            pattern = rf"\b{re.escape(code)}\b"
            if re.search(pattern, text, re.IGNORECASE):
                if code not in found_subs:
                    found_subs.append(code)

        if found_subs:
            resolved["subsidiary"] = found_subs[0]
            resolved["subsidiaries"] = found_subs

        # 3. Mine Extraction
        for mine_name, sub_code in KNOWN_FLAGSHIP_MINES.items():
            pattern = rf"\b{re.escape(mine_name)}\b"
            if re.search(pattern, lowered):
                resolved["mine"] = mine_name.title()
                if not resolved["subsidiary"]:
                    resolved["subsidiary"] = sub_code
                    if sub_code not in resolved["subsidiaries"]:
                        resolved["subsidiaries"].append(sub_code)
                break

        # Check regex for general mine naming: "X OCP", "Y Colliery", "Z Mine"
        if not resolved["mine"]:
            mine_m = re.search(r"\b([A-Za-z0-9-]+)\s+(?:OCP|UG|OC|Colliery|Mine|Block)\b", text, re.IGNORECASE)
            if mine_m:
                resolved["mine"] = mine_m.group(0).strip()

        # 4. Metric Resolution
        # Use word-boundary search across metric aliases (longest match first)
        sorted_aliases = sorted(METRIC_ALIASES.items(), key=lambda x: len(x[0]), reverse=True)
        for alias, code in sorted_aliases:
            pattern = rf"\b{re.escape(alias)}\b"
            if re.search(pattern, lowered):
                resolved["metric_code"] = code
                resolved["metric_name"] = metric_registry.get_canonical_name(code)
                resolved["unit"] = metric_registry.get_default_unit(code)
                resolved["raw_matched_metric"] = alias
                break

        # If not found via direct aliases, test with metric_registry.resolve
        if not resolved["metric_code"]:
            metric_match = metric_registry.resolve(lowered)
            if metric_match:
                resolved["metric_code"] = metric_match[0]
                resolved["metric_name"] = metric_match[1]
                resolved["unit"] = metric_match[2]

        return resolved
