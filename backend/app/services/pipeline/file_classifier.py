"""
File Classifier — Determines SourceType and mining document category.
Deterministic rule-based classification based on MIME, extension, structure, and keyword heuristics.
"""
import re
from typing import Union
from app.models.enums import FileType, SourceType


class FileClassifier:
    @classmethod
    def classify_source_type(cls, file_type: Union[FileType, str], is_scanned: bool = False) -> SourceType:
        val = file_type.value if hasattr(file_type, "value") else str(file_type).upper()

        if val == "PDF":
            return SourceType.SCANNED_PDF if is_scanned else SourceType.DIGITAL_PDF
        elif val == "XLSX":
            return SourceType.XLSX
        elif val == "XLS":
            return SourceType.XLS
        elif val == "CSV":
            return SourceType.CSV
        elif val in ("PNG", "JPG", "JPEG"):
            return SourceType.IMAGE
        elif val == "TXT":
            return SourceType.TXT
        return SourceType.UNKNOWN

    @classmethod
    def classify_document_category(cls, filename: str, content_preview: str) -> str:
        """
        Infers mining document category from filename tokens and document text preview.
        """
        text = f"{filename} {content_preview}".lower()

        if any(w in text for w in ["annual report", "annual account", "director's report", "integrated annual report"]):
            return "ANNUAL_REPORT"
        if any(w in text for w in ["production", "offtake", "despatch", "overburden", "stripping ratio", "bcm", "raw coal"]):
            return "PRODUCTION_REPORT"
        if any(w in text for w in ["drill", "borehole", "coring", "lithology", "strata"]):
            return "DRILLING_LOG"
        if any(w in text for w in ["geological", "cmpdi report", "exploration", "coal reserve", "grade g1", "grade g"]):
            return "GEOLOGICAL_REPORT"
        if any(w in text for w in ["mine plan", "mining plan", "environmental clearance", "project report", "mine closure"]):
            return "MINE_PLAN"
        if any(w in text for w in ["financial", "balance sheet", "p&l", "profit and loss", "ebitda"]):
            return "FINANCIAL_REPORT"

        return "GENERAL_REPORT"
