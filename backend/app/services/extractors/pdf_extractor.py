"""
PDF Extractor — Comprehensive PDF extraction using PyMuPDF (fitz).
Extracts text, detected tables (via page.find_tables()), embedded images, and detects scanned pages.
For scanned pages: integrates quality assessment, multi-candidate enhancement, and OCR fallback.
"""
from typing import Dict, Any, List, Optional
import pymupdf as fitz
from app.core.logging import logger
from app.services.ocr import ocr_provider
from app.services.pipeline.quality_assessment import QualityAssessmentService
from app.services.pipeline.enhancement import DocumentEnhancementService


class PDFExtractor:
    @staticmethod
    def extract(file_path: str) -> Dict[str, Any]:
        """
        Extracts native text, tables, and page metadata from PDF.
        Falls back to enhancement + OCR for scanned or empty pages.
        Handles mixed digital and scanned documents page by page.
        """
        doc = fitz.open(file_path)
        page_count = len(doc)
        pages_data: List[Dict[str, Any]] = []
        tables_data: List[Dict[str, Any]] = []
        full_text_list: List[str] = []
        is_scanned_overall = True
        total_chars = 0
        table_global_idx = 0

        for page_idx in range(page_count):
            page_num = page_idx + 1
            page = doc[page_idx]

            # 1. Native text extraction
            native_text = page.get_text("text") or ""
            char_count = len(native_text.strip())
            total_chars += char_count

            # A page is considered digital if it has > 50 characters of native text
            has_native = char_count > 50
            if has_native:
                is_scanned_overall = False

            extracted_text = native_text
            ocr_applied = False
            ocr_confidence = None
            page_quality = None
            enhancement_applied = False

            # 2. If page is scanned / minimal text, trigger quality check + enhancement + OCR
            if not has_native:
                try:
                    pix = page.get_pixmap(dpi=200)
                    img_bytes = pix.tobytes("png")
                    
                    # Assess quality of this page scan
                    page_quality = QualityAssessmentService.assess_image_data(img_bytes)
                    
                    if ocr_provider.is_available():
                        # If poor quality, run multi-candidate enhancement
                        if page_quality.get("enhancement_recommended", False):
                            candidates = DocumentEnhancementService.generate_candidates(img_bytes)
                            best_name, ocr_txt, conf, blocks = ocr_provider.evaluate_candidates(candidates, page_number=page_num)
                            enhancement_applied = (best_name != "original")
                        else:
                            ocr_res = ocr_provider.extract_with_fallback(img_bytes, page_number=page_num)
                            ocr_txt = ocr_res.get("text", "")
                            conf = ocr_res.get("confidence", 0.0)

                        if ocr_txt:
                            extracted_text = ocr_txt
                            ocr_applied = True
                            ocr_confidence = conf

                except Exception as e:
                    logger.warning(f"Error processing scanned page {page_num} in {file_path}: {e}")

            full_text_list.append(f"--- Page {page_num} ---\n{extracted_text}")

            # 3. Table extraction using PyMuPDF table finder
            page_tables_found = False
            try:
                tabs = page.find_tables()
                for t in tabs:
                    df = t.extract()
                    if df and len(df) > 1:
                        headers = [str(c).strip() if c is not None else f"Col_{i}" for i, c in enumerate(df[0])]
                        rows = []
                        for r_idx, r in enumerate(df[1:]):
                            row_dict = {}
                            for c_idx, val in enumerate(r):
                                col_name = headers[c_idx] if c_idx < len(headers) else f"Col_{c_idx}"
                                row_dict[col_name] = str(val).strip() if val is not None else ""
                            rows.append(row_dict)

                        table_info = {
                            "table_index": table_global_idx,
                            "page_number": page_num,
                            "sheet_name": f"Page_{page_num}_Table_{table_global_idx + 1}",
                            "headers": headers,
                            "row_count": len(rows),
                            "column_count": len(headers),
                            "data": rows,
                            "raw_text": "\n".join([", ".join(str(c) for c in r) for r in df]),
                            "confidence": 0.95,
                            "structure_status": "CLEAN"
                        }
                        tables_data.append(table_info)
                        table_global_idx += 1
                        page_tables_found = True
            except Exception as e:
                logger.warning(f"Table finder failed on page {page_num}: {e}")

            # 4. If scanned and no native tables found, attempt OCR table reconstruction
            if not has_native and not page_tables_found and ocr_applied:
                try:
                    reconstructed = ocr_provider.extract_table_text(img_bytes)
                    if reconstructed and len(reconstructed) > 1:
                        headers = [str(c) for c in reconstructed[0]]
                        rec_rows = []
                        for row in reconstructed[1:]:
                            rec_rows.append({
                                headers[i] if i < len(headers) else f"Col_{i}": str(val)
                                for i, val in enumerate(row)
                            })
                        tables_data.append({
                            "table_index": table_global_idx,
                            "page_number": page_num,
                            "sheet_name": f"Page_{page_num}_OCR_Table",
                            "headers": headers,
                            "row_count": len(rec_rows),
                            "column_count": len(headers),
                            "data": rec_rows,
                            "raw_text": "\n".join([", ".join(r) for r in reconstructed]),
                            "confidence": 0.70,
                            "structure_status": "TABLE_STRUCTURE_UNCERTAIN"
                        })
                        table_global_idx += 1
                except Exception:
                    pass

            # 5. Image count
            image_list = page.get_images(full=True)

            pages_data.append({
                "page_number": page_num,
                "text": extracted_text,
                "char_count": len(extracted_text),
                "has_native_text": has_native,
                "ocr_applied": ocr_applied,
                "ocr_confidence": ocr_confidence,
                "image_count": len(image_list),
                "quality": page_quality,
                "enhancement_applied": enhancement_applied
            })

        doc.close()

        return {
            "page_count": page_count,
            "total_chars": total_chars,
            "is_scanned": is_scanned_overall,
            "pages": pages_data,
            "tables": tables_data,
            "text": "\n\n".join(full_text_list)
        }
