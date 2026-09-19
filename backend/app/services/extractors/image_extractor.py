"""
Image Extractor — Handles PNG, JPG, JPEG extraction.
Performs image loading, quality assessment, multi-candidate enhancement,
and OCR with bounding block provenance.
"""
import os
from typing import Dict, Any, List
from PIL import Image

from app.core.logging import logger
from app.services.ocr import ocr_provider
from app.services.pipeline.quality_assessment import QualityAssessmentService
from app.services.pipeline.enhancement import DocumentEnhancementService


class ImageExtractor:
    @staticmethod
    def extract(file_path: str) -> Dict[str, Any]:
        filename = os.path.basename(file_path)
        with Image.open(file_path) as img:
            width, height = img.size
            img_format = img.format

        with open(file_path, "rb") as f:
            image_bytes = f.read()

        # 1. Assess quality
        quality_eval = QualityAssessmentService.assess_image_data(image_bytes)
        enhancement_applied = False
        enhancement_method = "none"

        # 2. OCR candidate evaluation
        text = ""
        avg_confidence = 0.0
        blocks = []
        tables_data = []

        if ocr_provider.is_available():
            if quality_eval.get("enhancement_recommended", False):
                candidates = DocumentEnhancementService.generate_candidates(image_bytes)
                best_name, text, avg_confidence, blocks = ocr_provider.evaluate_candidates(candidates, page_number=1)
                enhancement_applied = (best_name != "original")
                enhancement_method = best_name
            else:
                ocr_result = ocr_provider.extract_with_fallback(image_bytes, page_number=1)
                text = ocr_result.get("text", "")
                avg_confidence = ocr_result.get("confidence", 0.0)
                blocks = ocr_result.get("blocks", [])

            # 3. Attempt table reconstruction from OCR blocks if any
            table_rows = ocr_provider.extract_table_text(image_bytes)
            if table_rows and len(table_rows) > 1:
                headers = [str(c) for c in table_rows[0]]
                rec_data = []
                for row in table_rows[1:]:
                    rec_data.append({
                        headers[i] if i < len(headers) else f"Col_{i}": str(val)
                        for i, val in enumerate(row)
                    })
                tables_data.append({
                    "table_index": 0,
                    "sheet_name": f"{filename}_OCR_Table",
                    "headers": headers,
                    "row_count": len(rec_data),
                    "column_count": len(headers),
                    "data": rec_data,
                    "raw_text": "\n".join([", ".join(r) for r in table_rows]),
                    "confidence": 0.75,
                    "structure_status": "TABLE_STRUCTURE_UNCERTAIN"
                })

        page_data = {
            "page_number": 1,
            "text": text,
            "char_count": len(text),
            "has_native_text": False,
            "ocr_applied": True,
            "ocr_confidence": avg_confidence,
            "image_count": 1,
            "blocks": [b.to_dict() for b in blocks],
            "quality": quality_eval,
            "enhancement_applied": enhancement_applied,
            "enhancement_method": enhancement_method
        }

        return {
            "page_count": 1,
            "total_chars": len(text),
            "is_scanned": True,
            "image_format": img_format,
            "dimensions": {"width": width, "height": height},
            "pages": [page_data],
            "tables": tables_data,
            "text": text,
            "ocr_confidence": avg_confidence,
            "quality": quality_eval,
            "enhancement_applied": enhancement_applied
        }
