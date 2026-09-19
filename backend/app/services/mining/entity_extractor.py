"""
MiningEntityExtractor — Extracts mining-specific entities (subsidiary, mine, project, seam, period)
using deterministic regex matching and dictionary lookup. No LLM hallucination.
"""
import re
from typing import Dict, Any, Optional, List
from app.services.mining.org_normalizer import OrgNormalizer, VALID_SUBSIDIARIES
from app.services.mining.period_normalizer import PeriodNormalizer


class MiningEntityExtractor:
    # Regex patterns for Indian coal mining terminology
    SEAM_PATTERN = re.compile(r'\b(?:seam\s*[-–:]?\s*([IVXLCDM\d]+[A-Z]?|top|bottom|middle|comb(?:ined)?))\b', re.IGNORECASE)
    MINE_PATTERN = re.compile(r'\b([A-Za-z0-9\s-]+?)\s+(?:OCP|UG|OC|Colliery|Mine|Block)\b', re.IGNORECASE)
    PROJECT_PATTERN = re.compile(r'\b(?:Project|Area|Division)\s*[-–:]?\s*([A-Za-z0-9\s-]+)\b', re.IGNORECASE)

    @classmethod
    def extract_entities_from_text(cls, text: str) -> Dict[str, Any]:
        """
        Extracts mining entities present in the given text snippet.
        Returns dict with keys: subsidiary, period, seam, mine, project.
        """
        entities: Dict[str, Any] = {
            "subsidiary": None,
            "period": None,
            "seam": None,
            "mine": None,
            "project": None,
        }
        if not text:
            return entities

        # 1. Subsidiary detection (deterministic: earliest appearance in text / title)
        earliest_pos = None
        for sub in VALID_SUBSIDIARIES:
            pattern = rf'\b{sub}\b'
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                if earliest_pos is None or m.start() < earliest_pos[0]:
                    earliest_pos = (m.start(), sub)
        if earliest_pos:
            entities["subsidiary"] = earliest_pos[1]

        # 2. Period detection
        entities["period"] = PeriodNormalizer.extract_period(text)

        # 3. Seam detection
        seam_match = cls.SEAM_PATTERN.search(text)
        if seam_match:
            entities["seam"] = f"Seam {seam_match.group(1).strip().upper()}"

        # 4. Mine / Colliery detection
        mine_match = cls.MINE_PATTERN.search(text)
        if mine_match:
            mine_name = mine_match.group(0).strip()
            # Avoid matching too long or generic phrases
            if len(mine_name.split()) <= 4:
                entities["mine"] = mine_name

        # 5. Project detection
        proj_match = cls.PROJECT_PATTERN.search(text)
        if proj_match:
            proj_name = proj_match.group(1).strip()
            if len(proj_name.split()) <= 4:
                entities["project"] = proj_name

        return entities

    @classmethod
    def find_subsidiary_in_tokens(cls, tokens: List[str]) -> Optional[str]:
        for token in tokens:
            norm = OrgNormalizer.normalize_org(token)
            if norm in VALID_SUBSIDIARIES:
                return norm
        return None
