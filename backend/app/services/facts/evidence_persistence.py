"""
EvidencePersistenceService — Persists extracted facts into the Evidence Ledger.
Handles deduplication, coordinate validation, validation status assignment,
and document fact count + average confidence synchronization.
"""
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.fact import ExtractedFact
from app.models.document import Document
from app.models.audit import AuditEvent
from app.models.enums import AuditAction, ValidationStatus
from app.services.facts.confidence_engine import ConfidenceEngine


class EvidencePersistenceService:
    @classmethod
    def persist_facts(
        cls,
        db: Session,
        document_id: str,
        facts_data: List[Dict[str, Any]]
    ) -> List[ExtractedFact]:
        """
        Saves a list of extracted fact dicts into the database.
        De-duplicates based on document_id + metric_code + reporting_period + subsidiary + coordinates.
        """
        saved_facts = []

        for item in facts_data:
            conf = item.get("confidence_score", 0.8)
            val_status = item.get("validation_status") or ConfidenceEngine.get_initial_validation_status(conf)

            # Build query to check for existing identical fact
            existing_query = db.query(ExtractedFact).filter(
                ExtractedFact.document_id == document_id,
                ExtractedFact.metric_code == item.get("metric_code"),
                ExtractedFact.reporting_period == item.get("reporting_period"),
                ExtractedFact.subsidiary == item.get("subsidiary"),
                ExtractedFact.page_number == item.get("page_number"),
                ExtractedFact.cell_reference == item.get("cell_reference"),
                ExtractedFact.row_number == item.get("row_number")
            )
            existing = existing_query.first()

            if existing:
                existing.numeric_value = item["numeric_value"]
                existing.unit = item.get("unit")
                existing.raw_unit = item.get("raw_unit")
                existing.confidence_score = conf
                existing.validation_status = val_status
                existing.source_context = item.get("source_context", existing.source_context)
                saved_facts.append(existing)
            else:
                new_fact = ExtractedFact(
                    document_id=document_id,
                    metric_name=item["metric_name"],
                    metric_code=item["metric_code"],
                    raw_metric_name=item.get("raw_metric_name"),
                    numeric_value=item["numeric_value"],
                    unit=item.get("unit"),
                    raw_unit=item.get("raw_unit"),
                    reporting_period=item.get("reporting_period"),
                    organization="Coal India Limited",
                    subsidiary=item.get("subsidiary"),
                    mine=item.get("mine"),
                    location=item.get("location"),
                    confidence_score=conf,
                    extraction_method=item.get("extraction_method"),
                    page_number=item.get("page_number"),
                    sheet_name=item.get("sheet_name"),
                    row_number=item.get("row_number"),
                    column_name=item.get("column_name"),
                    cell_reference=item.get("cell_reference"),
                    table_reference=item.get("table_reference"),
                    source_context=item.get("source_context", ""),
                    validation_status=val_status,
                    human_verified=False
                )
                db.add(new_fact)
                saved_facts.append(new_fact)

        db.flush()

        # Update document fact count and average confidence
        total_facts = db.query(ExtractedFact).filter(ExtractedFact.document_id == document_id).count()
        avg_conf = db.query(func.avg(ExtractedFact.confidence_score)).filter(
            ExtractedFact.document_id == document_id
        ).scalar()

        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.fact_count = total_facts
            if avg_conf is not None:
                doc.average_confidence = round(float(avg_conf), 2)

        db.commit()
        return saved_facts
