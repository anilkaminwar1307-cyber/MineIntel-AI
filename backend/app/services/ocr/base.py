"""
OCR Provider base abstraction for MineIntel.
Defines common data structures and abstract interface for all OCR engines.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple, Union
import numpy as np
from PIL import Image
import io


class OCRBlock:
    """Represents a block/line of OCR-recognized text with positional provenance coordinates."""
    def __init__(
        self,
        text: str,
        confidence: float = 1.0,
        bbox: Optional[Tuple[int, int, int, int]] = None,
        line_number: int = 0,
        block_number: int = 0,
        page_number: int = 1
    ):
        self.text = text.strip()
        self.confidence = max(0.0, min(1.0, float(confidence)))   # 0.0-1.0
        self.bbox = bbox                                           # (x0, y0, x1, y1)
        self.line_number = line_number
        self.block_number = block_number
        self.page_number = page_number

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "confidence": round(self.confidence, 3),
            "bbox": list(self.bbox) if self.bbox else None,
            "line_number": self.line_number,
            "block_number": self.block_number,
            "page_number": self.page_number,
        }


class OCRProvider(ABC):
    """Abstract base for OCR providers. Implementations must be stateless and idempotent."""

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if this provider is installed, configured, and functional."""
        ...

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Returns provider status dict with 'available' bool, 'provider' name, and details."""
        ...

    @abstractmethod
    def extract_text(self, image: Union[bytes, Image.Image, np.ndarray]) -> str:
        """Extract plain text from image input. Returns empty string if nothing found."""
        ...

    @abstractmethod
    def extract_blocks(self, image: Union[bytes, Image.Image, np.ndarray], page_number: int = 1) -> List[OCRBlock]:
        """Extract text blocks with coordinates and individual confidence scores."""
        ...

    def extract_table_text(self, image: Union[bytes, Image.Image, np.ndarray]) -> List[List[str]]:
        """
        Optional heuristic table text reconstruction from OCR blocks.
        Default implementation groups text blocks by vertical alignment.
        """
        blocks = self.extract_blocks(image)
        if not blocks:
            return []
        # Sort blocks by y coordinate, then x coordinate
        valid_blocks = [b for b in blocks if b.bbox and b.text]
        if not valid_blocks:
            lines = [b.text for b in blocks if b.text]
            return [[line] for line in lines]

        valid_blocks.sort(key=lambda b: (b.bbox[1] // 15, b.bbox[0]))
        rows: List[List[str]] = []
        current_y_bucket = None
        current_row: List[str] = []

        for b in valid_blocks:
            y_bucket = b.bbox[1] // 15
            if current_y_bucket is None or y_bucket == current_y_bucket:
                current_y_bucket = y_bucket
                current_row.append(b.text)
            else:
                if current_row:
                    rows.append(current_row)
                current_row = [b.text]
                current_y_bucket = y_bucket

        if current_row:
            rows.append(current_row)
        return rows

    def average_confidence(self, blocks: List[OCRBlock]) -> float:
        """Calculate average OCR confidence from a list of blocks."""
        if not blocks:
            return 0.0
        return sum(b.confidence for b in blocks) / len(blocks)

    @staticmethod
    def to_pil_image(image: Union[bytes, Image.Image, np.ndarray]) -> Image.Image:
        """Helper to safely convert supported input formats into a PIL Image."""
        if isinstance(image, Image.Image):
            return image
        if isinstance(image, bytes):
            return Image.open(io.BytesIO(image))
        if isinstance(image, np.ndarray):
            import cv2
            if len(image.shape) == 2:
                return Image.fromarray(image)
            # assume BGR from OpenCV
            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            return Image.fromarray(rgb)
        raise ValueError(f"Unsupported image input type: {type(image)}")
