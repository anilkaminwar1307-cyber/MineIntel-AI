"""
PaddleOCR Provider — Preferred primary OCR engine for MineIntel.
Attempts dynamic loading of PaddleOCR. If installed, performs high-accuracy OCR.
If not installed or model unavailable, reports available=False without crashing.
"""
import os
from typing import List, Dict, Any, Union
import numpy as np
from PIL import Image

from app.core.logging import logger
from app.services.ocr.base import OCRProvider, OCRBlock

_PADDLE_LOADED = False
_PADDLE_ENGINE = None

try:
    from paddleocr import PaddleOCR
    _PADDLE_LOADED = True
except Exception:
    _PADDLE_LOADED = False


class PaddleOCRProvider(OCRProvider):
    """
    Preferred OCR engine. Uses PaddleOCR for multilingual and layout-aware character recognition.
    """

    def __init__(self):
        self._engine = None
        self._initialized = False

    def _ensure_engine(self) -> bool:
        if self._initialized:
            return self._engine is not None
        self._initialized = True
        if not _PADDLE_LOADED:
            return False
        try:
            # Initialize with angle classification enabled
            self._engine = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
            return True
        except Exception as e:
            logger.warning(f"Failed to initialize PaddleOCR engine: {e}")
            self._engine = None
            return False

    def is_available(self) -> bool:
        return self._ensure_engine()

    def health_check(self) -> Dict[str, Any]:
        avail = self.is_available()
        return {
            "provider": "PaddleOCR",
            "available": avail,
            "preferred": True,
            "library_installed": _PADDLE_LOADED,
            "note": "Operational" if avail else "PaddleOCR library not installed or model failed to load"
        }

    def extract_text(self, image: Union[bytes, Image.Image, np.ndarray]) -> str:
        if not self.is_available():
            return ""
        try:
            pil_img = self.to_pil_image(image)
            img_np = np.array(pil_img)
            result = self._engine.ocr(img_np, cls=True)
            if not result or not result[0]:
                return ""
            lines = []
            for line in result[0]:
                if line and len(line) >= 2 and line[1]:
                    text = str(line[1][0]).strip()
                    if text:
                        lines.append(text)
            return "\n".join(lines)
        except Exception as e:
            logger.warning(f"PaddleOCR extract_text error: {e}")
            return ""

    def extract_blocks(self, image: Union[bytes, Image.Image, np.ndarray], page_number: int = 1) -> List[OCRBlock]:
        if not self.is_available():
            return []
        try:
            pil_img = self.to_pil_image(image)
            img_np = np.array(pil_img)
            result = self._engine.ocr(img_np, cls=True)
            if not result or not result[0]:
                return []

            blocks: List[OCRBlock] = []
            for idx, item in enumerate(result[0]):
                if not item or len(item) < 2:
                    continue
                box, (text, conf) = item[0], item[1]
                text = str(text).strip()
                if not text:
                    continue
                # box is [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]
                x_coords = [p[0] for p in box]
                y_coords = [p[1] for p in box]
                bbox = (int(min(x_coords)), int(min(y_coords)), int(max(x_coords)), int(max(y_coords)))

                blocks.append(OCRBlock(
                    text=text,
                    confidence=float(conf),
                    bbox=bbox,
                    line_number=idx + 1,
                    block_number=idx + 1,
                    page_number=page_number
                ))
            return blocks
        except Exception as e:
            logger.warning(f"PaddleOCR extract_blocks error: {e}")
            return []
