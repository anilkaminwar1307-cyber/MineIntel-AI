"""
Stub OCR provider used when no real OCR engine is available.
Guarantees the pipeline never crashes when OCR software is absent.
"""
from typing import List, Dict, Any, Union
import numpy as np
from PIL import Image
from app.services.ocr.base import OCRProvider, OCRBlock


class UnavailableOCRProvider(OCRProvider):
    """Returns empty results and clearly marks OCR as unavailable."""

    def is_available(self) -> bool:
        return False

    def health_check(self) -> Dict[str, Any]:
        return {
            "provider": "Unavailable",
            "available": False,
            "preferred": False,
            "note": "No OCR provider available (neither PaddleOCR nor Tesseract binary detected)"
        }

    def extract_text(self, image: Union[bytes, Image.Image, np.ndarray]) -> str:
        return ""

    def extract_blocks(self, image: Union[bytes, Image.Image, np.ndarray], page_number: int = 1) -> List[OCRBlock]:
        return []
