"""
OCR Manager — Chained OCR provider abstraction for MineIntel.
Implements the preferred (PaddleOCR) -> fallback (Tesseract) -> graceful degradation (Unavailable) chain.
Provides multi-candidate OCR evaluation for enhanced scans.
"""
from typing import List, Dict, Any, Union, Tuple, Optional
import numpy as np
from PIL import Image

from app.core.logging import logger
from app.services.ocr.base import OCRProvider, OCRBlock
from app.services.ocr.paddleocr_provider import PaddleOCRProvider
from app.services.ocr.tesseract_provider import TesseractProvider
from app.services.ocr.unavailable_provider import UnavailableOCRProvider


class OCRManager(OCRProvider):
    def __init__(self):
        self.paddle = PaddleOCRProvider()
        self.tesseract = TesseractProvider()
        self.unavailable = UnavailableOCRProvider()

    def get_active_provider(self) -> OCRProvider:
        if self.paddle.is_available():
            return self.paddle
        if self.tesseract.is_available():
            return self.tesseract
        return self.unavailable

    def is_available(self) -> bool:
        return self.paddle.is_available() or self.tesseract.is_available()

    def health_check(self) -> Dict[str, Any]:
        paddle_h = self.paddle.health_check()
        tess_h = self.tesseract.health_check()
        active = self.get_active_provider()
        return {
            "available": self.is_available(),
            "active_provider": active.health_check().get("provider", "None"),
            "paddle_ocr": paddle_h,
            "tesseract": tess_h,
        }

    def extract_text(self, image: Union[bytes, Image.Image, np.ndarray]) -> str:
        res = self.extract_with_fallback(image)
        return res.get("text", "")

    def extract_blocks(self, image: Union[bytes, Image.Image, np.ndarray], page_number: int = 1) -> List[OCRBlock]:
        res = self.extract_with_fallback(image, page_number=page_number)
        return res.get("blocks", [])

    def extract_with_fallback(
        self,
        image: Union[bytes, Image.Image, np.ndarray],
        page_number: int = 1
    ) -> Dict[str, Any]:
        """
        Executes OCR with automatic fallback:
        1. Try PaddleOCR (if available)
        2. If fails or unavailable, try Tesseract
        3. If both unavailable, returns empty text with warning
        Returns: {
            "text": str,
            "blocks": List[OCRBlock],
            "confidence": float,
            "provider_used": str,
            "fallback_applied": bool
        }
        """
        fallback_applied = False
        provider_used = "None"

        # 1. Try PaddleOCR
        if self.paddle.is_available():
            try:
                blocks = self.paddle.extract_blocks(image, page_number=page_number)
                text = "\n".join([b.text for b in blocks if b.text])
                conf = self.paddle.average_confidence(blocks) if blocks else 0.0
                return {
                    "text": text,
                    "blocks": blocks,
                    "confidence": round(conf, 3),
                    "provider_used": "PaddleOCR",
                    "fallback_applied": False
                }
            except Exception as e:
                logger.warning(f"PaddleOCR execution failed: {e}. Falling back to Tesseract.")
                fallback_applied = True

        # 2. Try Tesseract
        if self.tesseract.is_available():
            try:
                blocks = self.tesseract.extract_blocks(image, page_number=page_number)
                text = "\n".join([b.text for b in blocks if b.text])
                conf = self.tesseract.average_confidence(blocks) if blocks else 0.0
                return {
                    "text": text,
                    "blocks": blocks,
                    "confidence": round(conf, 3),
                    "provider_used": "Tesseract",
                    "fallback_applied": fallback_applied
                }
            except Exception as e:
                logger.warning(f"Tesseract execution failed: {e}.")

        # 3. Fallback to unavailable
        return {
            "text": "",
            "blocks": [],
            "confidence": 0.0,
            "provider_used": "Unavailable",
            "fallback_applied": True,
            "warning": "No OCR engine available on system"
        }

    def evaluate_candidates(
        self,
        candidates: Dict[str, bytes],
        page_number: int = 1
    ) -> Tuple[str, str, float, List[OCRBlock]]:
        """
        Evaluates multiple enhancement candidates, compares OCR confidence,
        and selects the best candidate result.
        Returns: (best_candidate_name, best_text, best_confidence, best_blocks)
        """
        if not self.is_available() or not candidates:
            orig = candidates.get("original", b"")
            return "original", "", 0.0, []

        best_name = "original"
        best_text = ""
        best_conf = -1.0
        best_blocks: List[OCRBlock] = []

        for name, img_bytes in candidates.items():
            res = self.extract_with_fallback(img_bytes, page_number=page_number)
            text = res["text"]
            conf = res["confidence"]
            blocks = res["blocks"]
            # Consider text length and confidence
            effective_score = conf * (1.0 if len(text) > 20 else 0.5)
            if effective_score > best_conf or (best_conf < 0 and text):
                best_conf = effective_score
                best_name = name
                best_text = text
                best_blocks = blocks

        return best_name, best_text, max(0.0, round(best_conf, 3)), best_blocks
