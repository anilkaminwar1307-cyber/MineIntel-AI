"""
Organization and Subsidiary normalizer for Coal India Limited & CMPDI ecosystem.
Deterministic mapping only. No LLM involved.
"""
from typing import Optional, Dict, Tuple

# Canonical subsidiaries and organizations in Indian Coal Sector
ORGANIZATION_MAP: Dict[str, Tuple[str, str]] = {
    # Key: normalized alias -> (Canonical Code, Full Name)
    "cil": ("CIL", "Coal India Limited"),
    "coal india": ("CIL", "Coal India Limited"),
    "coal india limited": ("CIL", "Coal India Limited"),
    
    "ecl": ("ECL", "Eastern Coalfields Limited"),
    "eastern coalfields": ("ECL", "Eastern Coalfields Limited"),
    "eastern coalfields limited": ("ECL", "Eastern Coalfields Limited"),
    
    "bccl": ("BCCL", "Bharat Coking Coal Limited"),
    "bharat coking coal": ("BCCL", "Bharat Coking Coal Limited"),
    "bharat coking coal limited": ("BCCL", "Bharat Coking Coal Limited"),
    
    "ccl": ("CCL", "Central Coalfields Limited"),
    "central coalfields": ("CCL", "Central Coalfields Limited"),
    "central coalfields limited": ("CCL", "Central Coalfields Limited"),
    
    "wcl": ("WCL", "Western Coalfields Limited"),
    "western coalfields": ("WCL", "Western Coalfields Limited"),
    "western coalfields limited": ("WCL", "Western Coalfields Limited"),
    
    "secl": ("SECL", "South Eastern Coalfields Limited"),
    "south eastern coalfields": ("SECL", "South Eastern Coalfields Limited"),
    "south eastern coalfields limited": ("SECL", "South Eastern Coalfields Limited"),
    
    "ncl": ("NCL", "Northern Coalfields Limited"),
    "northern coalfields": ("NCL", "Northern Coalfields Limited"),
    "northern coalfields limited": ("NCL", "Northern Coalfields Limited"),
    
    "mcl": ("MCL", "Mahanadi Coalfields Limited"),
    "mahanadi coalfields": ("MCL", "Mahanadi Coalfields Limited"),
    "mahanadi coalfields limited": ("MCL", "Mahanadi Coalfields Limited"),
    
    "cmpdi": ("CMPDI", "Central Mine Planning and Design Institute"),
    "cmpdil": ("CMPDI", "Central Mine Planning and Design Institute Limited"),
    "central mine planning and design institute": ("CMPDI", "Central Mine Planning and Design Institute"),
    
    "nec": ("NEC", "North Eastern Coalfields"),
    "north eastern coalfields": ("NEC", "North Eastern Coalfields"),
    
    "moc": ("MoC", "Ministry of Coal"),
    "ministry of coal": ("MoC", "Ministry of Coal"),
}

VALID_SUBSIDIARIES = ("CIL", "ECL", "BCCL", "CCL", "WCL", "SECL", "NCL", "MCL", "CMPDI", "NEC", "MoC")


class OrgNormalizer:
    @staticmethod
    def normalize_org(raw_name: Optional[str]) -> Optional[str]:
        """Returns canonical acronym (e.g. 'SECL') if recognized, else returns raw_name cleaned."""
        if not raw_name:
            return None
        cleaned = raw_name.strip()
        lowered = cleaned.lower()
        if lowered in ORGANIZATION_MAP:
            return ORGANIZATION_MAP[lowered][0]
        # Check if directly a recognized code (case-insensitive)
        for code in VALID_SUBSIDIARIES:
            if code.lower() == lowered:
                return code
        return cleaned

    @staticmethod
    def get_full_name(code: str) -> Optional[str]:
        for alias, (c, full_name) in ORGANIZATION_MAP.items():
            if c.upper() == code.upper():
                return full_name
        return None
