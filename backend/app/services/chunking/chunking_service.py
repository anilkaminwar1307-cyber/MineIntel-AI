"""
ChunkingService — Splits document content into structured chunks with provenance metadata.
Supports page-aware chunking and sliding window chunking with configurable overlap.
"""
import hashlib
from typing import List, Dict, Any, Optional


class ChunkingService:
    @staticmethod
    def compute_chunk_hash(text: str) -> str:
        return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()[:16]

    @classmethod
    def chunk_text(
        cls,
        text: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 150,
        page_number: Optional[int] = None,
        section: Optional[str] = None,
        document_id: Optional[str] = None,
        base_index: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Splits text into chunks of roughly `chunk_size` characters with `chunk_overlap`.
        Maintains paragraph/sentence boundaries where possible.
        """
        if not text or not text.strip():
            return []

        chunks: List[Dict[str, Any]] = []
        paragraphs = text.split("\n\n")
        
        current_chunk = ""
        current_index = base_index

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current_chunk) + len(para) + 2 <= chunk_size:
                current_chunk = f"{current_chunk}\n\n{para}" if current_chunk else para
            else:
                if current_chunk:
                    chunks.append({
                        "chunk_index": current_index,
                        "content": current_chunk,
                        "char_count": len(current_chunk),
                        "page_number": page_number,
                        "section": section,
                        "chunk_hash": cls.compute_chunk_hash(current_chunk),
                    })
                    current_index += 1

                # If the single paragraph itself is larger than chunk_size, split by sentences or chunk_size
                if len(para) > chunk_size:
                    start = 0
                    while start < len(para):
                        end = start + chunk_size
                        sub_text = para[start:end]
                        chunks.append({
                            "chunk_index": current_index,
                            "content": sub_text,
                            "char_count": len(sub_text),
                            "page_number": page_number,
                            "section": section,
                            "chunk_hash": cls.compute_chunk_hash(sub_text),
                        })
                        current_index += 1
                        start += (chunk_size - chunk_overlap)
                    current_chunk = ""
                else:
                    current_chunk = para

        if current_chunk:
            chunks.append({
                "chunk_index": current_index,
                "content": current_chunk,
                "char_count": len(current_chunk),
                "page_number": page_number,
                "section": section,
                "chunk_hash": cls.compute_chunk_hash(current_chunk),
            })

        return chunks
