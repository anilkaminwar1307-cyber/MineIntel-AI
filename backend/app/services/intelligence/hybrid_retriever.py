"""
Hybrid Evidence Retriever for Ask MineIntel.
Implements lexical BM25-style retrieval + metadata filtering + reranking.
Transparently labels retrieval method (no fake vector search if pgvector/embeddings are unavailable).
"""
import re
import math
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.document import Document, DocumentChunk
from app.core.logging import logger


STOPWORDS = {
    "what", "which", "where", "when", "who", "whom", "how", "show", "tell",
    "give", "explain", "about", "the", "and", "for", "with", "from", "that",
    "this", "these", "those", "have", "has", "had", "are", "were", "been",
    "will", "would", "shall", "should", "can", "could", "may", "might",
    "please", "report", "document", "data", "figure", "figures", "metric"
}


class HybridRetriever:
    """Retrieves document chunks using lexical term matching, metadata filters, and BM25 reranking."""

    @classmethod
    def retrieve(
        cls,
        db: Session,
        query: str,
        subsidiary: Optional[str] = None,
        period: Optional[str] = None,
        document_ids: Optional[List[str]] = None,
        include_demo: bool = False,
        limit: int = 6,
    ) -> Dict[str, Any]:
        """
        Executes metadata-filtered, BM25-scored lexical retrieval over DocumentChunk records.
        Returns matched chunks, scores, and explicit retrieval_method.
        """
        # 1. Normalize tokens
        words = [w for w in re.findall(r'\b\w{3,}\b', query.lower()) if w not in STOPWORDS]
        if not words:
            # Fallback to any alphabetic tokens >= 2 chars
            words = [w for w in re.findall(r'\b[a-zA-Z]{2,}\b', query.lower()) if w not in STOPWORDS]

        if not words:
            return {
                "chunks": [],
                "retrieval_method": "LEXICAL_BM25_RERANKED",
                "total_matched": 0,
            }

        # 2. Base Query with Metadata Filters
        chunk_query = db.query(DocumentChunk, Document).join(
            Document, Document.id == DocumentChunk.document_id
        )

        # Demo/Real Segregation
        if not include_demo:
            chunk_query = chunk_query.filter(Document.is_demo == False)  # noqa: E712
        else:
            # If demo only requested, filter is_demo == True
            pass

        # Selected Documents Filter
        if document_ids:
            chunk_query = chunk_query.filter(DocumentChunk.document_id.in_(document_ids))

        # Subsidiary Filter
        if subsidiary and subsidiary.upper() not in ("ALL", "CIL"):
            chunk_query = chunk_query.filter(
                or_(
                    Document.organization.ilike(f"%{subsidiary}%"),
                    Document.original_filename.ilike(f"%{subsidiary}%"),
                    DocumentChunk.content.ilike(f"%{subsidiary}%"),
                )
            )

        # 3. First-Pass Candidate Retrieval (Candidate matching on keywords)
        conditions = [DocumentChunk.content.ilike(f"%{w}%") for w in words[:6]]
        if not conditions:
            return {"chunks": [], "retrieval_method": "LEXICAL_BM25_RERANKED", "total_matched": 0}

        candidate_rows = chunk_query.filter(or_(*conditions)).limit(50).all()

        if not candidate_rows:
            return {
                "chunks": [],
                "retrieval_method": "LEXICAL_BM25_RERANKED",
                "total_matched": 0,
            }

        # 4. BM25-style Reranking
        # Compute term frequency and length penalty
        scored_candidates = []
        k1 = 1.5
        b = 0.75
        avg_len = sum(len(c.content.split()) for c, _ in candidate_rows) / max(1, len(candidate_rows))

        for chunk, doc in candidate_rows:
            content_lower = chunk.content.lower()
            tokens = content_lower.split()
            doc_len = len(tokens)

            score = 0.0
            for term in words:
                tf = content_lower.count(term)
                if tf > 0:
                    # BM25 tf component
                    denom = tf + k1 * (1 - b + b * (doc_len / max(1.0, avg_len)))
                    bm25_term = (tf * (k1 + 1)) / denom
                    score += bm25_term

            # Exact phrase bonus
            if len(words) >= 2 and " ".join(words[:2]) in content_lower:
                score += 3.0

            # Subsidiary match bonus
            if subsidiary and subsidiary.lower() in content_lower:
                score += 2.0

            # Period match bonus
            if period and period.lower() in content_lower:
                score += 2.0

            # Section header bonus
            if chunk.section and any(w in chunk.section.lower() for w in words):
                score += 1.5

            scored_candidates.append((score, chunk, doc))

        # Sort descending by score
        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        # 5. Build Top Results
        top_results = []
        seen_chunk_ids = set()
        for score, chunk, doc in scored_candidates:
            if chunk.id not in seen_chunk_ids and score > 0.5:
                seen_chunk_ids.add(chunk.id)
                top_results.append({
                    "chunk_id": chunk.id,
                    "document_id": doc.id,
                    "document_name": doc.original_filename,
                    "content": chunk.content,
                    "page_number": chunk.page_number,
                    "sheet_name": chunk.sheet_name,
                    "section": chunk.section,
                    "relevance_score": round(score, 3),
                    "is_demo": doc.is_demo,
                })
                if len(top_results) >= limit:
                    break

        return {
            "chunks": top_results,
            "retrieval_method": "LEXICAL_BM25_RERANKED",
            "total_matched": len(top_results),
        }
