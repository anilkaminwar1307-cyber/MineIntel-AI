"""
OCR package — exports the chained OCR manager as `ocr_provider`.
Supports preferred PaddleOCR, fallback Tesseract, and graceful Unavailable stub.
"""
from app.services.ocr.base import OCRProvider, OCRBlock
from app.services.ocr.paddleocr_provider import PaddleOCRProvider
from app.services.ocr.tesseract_provider import TesseractProvider
from app.services.ocr.unavailable_provider import UnavailableOCRProvider
from app.services.ocr.manager import OCRManager

# Singleton OCR manager with full fallback capabilities
ocr_provider = OCRManager()

__all__ = [
    "OCRProvider",
    "OCRBlock",
    "PaddleOCRProvider",
    "TesseractProvider",
    "UnavailableOCRProvider",
    "OCRManager",
    "ocr_provider"
]
