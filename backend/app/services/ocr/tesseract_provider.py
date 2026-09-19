"""
Tesseract OCR Provider.
Uses pytesseract as the bridge to the system Tesseract binary.
Discovers local Tesseract executable in PATH or standard installation locations.
Falls back gracefully if Tesseract is not installed on the host OS.
"""
import os
import shutil
from typing import List, Dict, Any, Union, Optional
import numpy as np
from PIL import Image

from app.core.logging import logger
from app.services.ocr.base import OCRProvider, OCRBlock

try:
    import pytesseract
    TESSERACT_IMPORT_OK = True
except ImportError:
    TESSERACT_IMPORT_OK = False


def _find_tesseract_binary() -> Optional[str]:
    """Finds tesseract binary on host system (Windows / Linux)."""
    if not TESSERACT_IMPORT_OK:
        return None

    # 1. Check if user configured path in environment
    env_path = os.environ.get("TESSERACT_PATH") or os.environ.get("TESSERACT_CMD")
    if env_path and os.path.exists(env_path):
        return env_path

    # 2. Check system PATH
    which_path = shutil.which("tesseract")
    if which_path:
        return which_path

    # 3. Standard Windows installation directories
    candidate_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
        os.path.expanduser(r"~\AppData\Local\Tesseract-OCR\tesseract.exe"),
    ]
    for cp in candidate_paths:
        if os.path.exists(cp):
            return cp

    return None


_FOUND_TESSERACT_PATH = _find_tesseract_binary()
if _FOUND_TESSERACT_PATH and TESSERACT_IMPORT_OK:
    try:
        pytesseract.pytesseract.tesseract_cmd = _FOUND_TESSERACT_PATH
    except Exception:
        pass


def _tesseract_binary_available() -> bool:
    if not TESSERACT_IMPORT_OK:
        return False
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


TESSERACT_AVAILABLE = _tesseract_binary_available()


class TesseractProvider(OCRProvider):
    """
    OCR via Tesseract. If Tesseract binary is not found on the host,
    all methods return empty / zero-confidence results rather than crashing.
    """

    def is_available(self) -> bool:
        global TESSERACT_AVAILABLE
        if not TESSERACT_AVAILABLE:
            TESSERACT_AVAILABLE = _tesseract_binary_available()
        return TESSERACT_AVAILABLE

    def health_check(self) -> Dict[str, Any]:
        avail = self.is_available()
        return {
            "provider": "Tesseract",
            "available": avail,
            "preferred": False,
            "binary_path": _FOUND_TESSERACT_PATH or "Not found",
            "library_installed": TESSERACT_IMPORT_OK,
            "note": "Operational" if avail else "Tesseract binary not found on host system"
        }

    def extract_text(self, image: Union[bytes, Image.Image, np.ndarray]) -> str:
        if not self.is_available():
            return ""
        try:
            pil_img = self.to_pil_image(image)
            text = pytesseract.image_to_string(pil_img, lang="eng")
            return text.strip()
        except Exception as e:
            logger.warning(f"Tesseract extract_text error: {e}")
            return ""

    def extract_blocks(self, image: Union[bytes, Image.Image, np.ndarray], page_number: int = 1) -> List[OCRBlock]:
        if not self.is_available():
            return []
        try:
            pil_img = self.to_pil_image(image)
            data = pytesseract.image_to_data(pil_img, lang="eng", output_type=pytesseract.Output.DICT)
            blocks: List[OCRBlock] = []
            for i, text in enumerate(data.get("text", [])):
                text = str(text).strip()
                if not text:
                    continue
                raw_conf = data["conf"][i]
                confidence = max(0.0, min(1.0, float(raw_conf) / 100.0)) if raw_conf != -1 else 0.0
                x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
                blocks.append(OCRBlock(
                    text=text,
                    confidence=confidence,
                    bbox=(x, y, x + w, y + h),
                    line_number=data.get("line_num", [0])[i],
                    block_number=data.get("block_num", [0])[i],
                    page_number=page_number,
                ))
            return blocks
        except Exception as e:
            logger.warning(f"Tesseract extract_blocks error: {e}")
            return []
