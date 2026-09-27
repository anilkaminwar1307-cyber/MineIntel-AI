import hashlib
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.fact import ExtractedFact
from app.models.document import Document
from app.models.validation import ValidationIssue, EvidenceConflict
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
        Generates automated validation issues and logs cross-document contradictions.
        """
        doc = db.query(Document).filter(Document.id == document_id).first()
        is_demo_doc = bool(doc.is_demo) if doc else False

        saved_facts = []
        warning_count = 0

        for item in facts_data:
            conf = item.get("confidence_score", 0.8)
            val_status = item.get("validation_status") or ConfidenceEngine.get_initial_validation_status(conf)

            # Compute deduplication key and source hash
            metric_code = item.get("metric_code", "UNKNOWN")
            rep_period = item.get("reporting_period") or ""
            sub = item.get("subsidiary") or ""
            mine_val = item.get("mine") or ""
            cell_ref = item.get("cell_reference") or ""
            page_n = item.get("page_number") or ""
            row_n = item.get("row_number") or ""

            dedup_key = f"{document_id}:{metric_code}:{rep_period}:{sub}:{mine_val}:{cell_ref}:{page_n}:{row_n}"
            source_content = f"{metric_code}:{item.get('numeric_value')}:{rep_period}:{item.get('source_context', '')}"
            source_hash = hashlib.sha256(source_content.encode("utf-8")).hexdigest()

            # Build query to check for existing identical fact in this document
            existing = db.query(ExtractedFact).filter(
                ExtractedFact.document_id == document_id,
                ExtractedFact.metric_code == metric_code,
                ExtractedFact.reporting_period == item.get("reporting_period"),
                ExtractedFact.subsidiary == item.get("subsidiary"),
                ExtractedFact.page_number == item.get("page_number"),
                ExtractedFact.cell_reference == item.get("cell_reference"),
                ExtractedFact.row_number == item.get("row_number")
            ).first()

            if existing:
                existing.numeric_value = item["numeric_value"]
                existing.unit = item.get("unit")
                existing.raw_unit = item.get("raw_unit")
                existing.confidence_score = conf
                existing.validation_status = val_status
                existing.source_context = item.get("source_context", existing.source_context)
                existing.source_hash = source_hash
                existing.dedup_key = dedup_key
                fact_obj = existing
                saved_facts.append(existing)
            else:
                new_fact = ExtractedFact(
                    document_id=document_id,
                    metric_name=item["metric_name"],
                    metric_code=metric_code,
                    raw_metric_name=item.get("raw_metric_name"),
                    numeric_value=item["numeric_value"],
                    unit=item.get("unit"),
                    raw_unit=item.get("raw_unit"),
                    reporting_period=item.get("reporting_period"),
                    organization=item.get("organization") or "Coal India Limited",
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
                    source_object_type=item.get("source_object_type", "TABLE" if item.get("cell_reference") else "PAGE"),
                    source_object_id=item.get("source_object_id"),
                    source_hash=source_hash,
                    dedup_key=dedup_key,
                    is_demo=is_demo_doc,
                    validation_status=val_status,
                    human_verified=False
                )
                db.add(new_fact)
                fact_obj = new_fact
                saved_facts.append(new_fact)

            db.flush()

            # Automated Validation Rules Check
            if not item.get("unit"):
                warning_count += 1
                db.add(ValidationIssue(
                    document_id=document_id,
                    fact_id=fact_obj.id,
                    issue_type="MISSING_UNIT",
                    severity="MEDIUM",
                    description=f"Extracted metric '{fact_obj.metric_name}' is missing canonical unit of measurement."
                ))

            if not item.get("reporting_period"):
                warning_count += 1
                db.add(ValidationIssue(
                    document_id=document_id,
                    fact_id=fact_obj.id,
                    issue_type="MISSING_PERIOD",
                    severity="MEDIUM",
                    description=f"Extracted metric '{fact_obj.metric_name}' does not specify an explicit reporting period."
                ))

            if conf < 0.75:
                warning_count += 1
                db.add(ValidationIssue(
                    document_id=document_id,
                    fact_id=fact_obj.id,
                    issue_type="LOW_CONFIDENCE",
                    severity="HIGH",
                    description=f"Extraction confidence score ({conf:.2f}) is below standard confidence threshold (0.75)."
                ))

            if metric_code == "UNMAPPED":
                warning_count += 1
                db.add(ValidationIssue(
                    document_id=document_id,
                    fact_id=fact_obj.id,
                    issue_type="UNMAPPED_METRIC",
                    severity="LOW",
                    description=f"Metric '{item.get('raw_metric_name')}' does not match standard CMPDI/CIL mining metric definitions."
                ))

            # Cross-document contradiction check (Rule 5: Never hide conflicts)
            if (
                fact_obj.metric_code
                and fact_obj.metric_code != "UNMAPPED"
                and fact_obj.reporting_period
                and fact_obj.subsidiary
                and fact_obj.numeric_value is not None
            ):
                conflicting = db.query(ExtractedFact).filter(
                    ExtractedFact.document_id != document_id,
                    ExtractedFact.metric_code == fact_obj.metric_code,
                    ExtractedFact.reporting_period == fact_obj.reporting_period,
                    ExtractedFact.subsidiary == fact_obj.subsidiary,
                    ExtractedFact.numeric_value.isnot(None),
                    ExtractedFact.numeric_value != fact_obj.numeric_value
                ).first()

                if conflicting and conflicting.numeric_value > 0:
                    diff_pct = abs(fact_obj.numeric_value - conflicting.numeric_value) / conflicting.numeric_value * 100
                    if diff_pct >= 5.0:  # 5% threshold
                        fact_obj.validation_status = ValidationStatus.CONFLICT.value
                        warning_count += 1
                        conflict = EvidenceConflict(
                            metric_code=fact_obj.metric_code,
                            primary_fact_id=conflicting.id,
                            conflicting_fact_id=fact_obj.id,
                            discrepancy_percent=round(diff_pct, 2),
                            status="OPEN",
                            description=(
                                f"Contradiction detected for {fact_obj.metric_name} ({fact_obj.subsidiary}, {fact_obj.reporting_period}): "
                                f"Existing document reports {conflicting.numeric_value} {conflicting.unit or ''} vs "
                                f"New upload reports {fact_obj.numeric_value} {fact_obj.unit or ''} ({diff_pct:.1f}% discrepancy)."
                            )
                        )
                        db.add(conflict)
                        db.add(ValidationIssue(
                            document_id=document_id,
                            fact_id=fact_obj.id,
                            issue_type="UNRESOLVED_CONFLICT",
                            severity="CRITICAL",
                            description=f"Contradicts existing record in Evidence Ledger: {conflicting.numeric_value} vs {fact_obj.numeric_value} ({diff_pct:.1f}% difference)."
                        ))

        db.flush()

        # Update document fact count, real_fact_count, warning_count, and average confidence
        total_facts = db.query(ExtractedFact).filter(ExtractedFact.document_id == document_id).count()
        avg_conf = db.query(func.avg(ExtractedFact.confidence_score)).filter(
            ExtractedFact.document_id == document_id
        ).scalar()

        if doc:
            doc.fact_count = total_facts
            if not is_demo_doc:
                doc.real_fact_count = total_facts
            doc.warning_count = warning_count
            if avg_conf is not None:
                doc.average_confidence = round(float(avg_conf), 2)

        db.commit()
        return saved_facts
