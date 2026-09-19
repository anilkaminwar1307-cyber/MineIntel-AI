"""
TXT Extractor — Plain text extraction with encoding detection.
Splits text into structured pages/sections for chunking and fact extraction.
"""
from typing import Dict, Any, List


class TXTExtractor:
    @staticmethod
    def extract(file_path: str) -> Dict[str, Any]:
        encodings = ["utf-8", "utf-8-sig", "latin1", "cp1252"]
        content = ""

        for enc in encodings:
            try:
                with open(file_path, "r", encoding=enc) as f:
                    content = f.read()
                break
            except Exception:
                continue

        # Split into logical pages (~3000 chars per page) if large
        page_chunks = [content[i:i+3000] for i in range(0, max(1, len(content)), 3000)]
        pages_data = []

        for p_idx, p_text in enumerate(page_chunks):
            pages_data.append({
                "page_number": p_idx + 1,
                "text": p_text,
                "char_count": len(p_text),
                "has_native_text": True,
                "ocr_applied": False,
                "ocr_confidence": None,
                "image_count": 0
            })

        return {
            "page_count": len(pages_data),
            "total_chars": len(content),
            "is_scanned": False,
            "pages": pages_data,
            "tables": [],
            "text": content
        }
