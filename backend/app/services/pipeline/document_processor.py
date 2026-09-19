"""
DocumentProcessor — Core Pipeline Orchestrator for Phase 2.
Orchestrates file classification, quality assessment, image enhancement, text/table extraction,
chunking, deterministic fact extraction, evidence persistence, and pipeline audit logging.
"""
import json
import os
import traceback
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.logging import logger
from app.models.document import Document, DocumentChunk
from app.models.processing import DocumentPage, DocumentSheet, DocumentTable, DocumentQuality, ProcessingLog
from app.models.fact import ExtractedFact
from app.models.audit import AuditEvent
from app.models.enums import DocumentStatus, FileType, AuditAction, ExtractionMethod

from app.services.pipeline.file_classifier import FileClassifier
from app.services.pipeline.quality_assessment import QualityAssessmentService
from app.services.pipeline.enhancement import DocumentEnhancementService
from app.services.extractors.pdf_extractor import PDFExtractor
from app.services.extractors.excel_extractor import ExcelExtractor
from app.services.extractors.csv_extractor import CSVExtractor
from app.services.extractors.image_extractor import ImageExtractor
from app.services.extractors.txt_extractor import TXTExtractor
from app.services.ocr import ocr_provider
from app.services.chunking.chunking_service import ChunkingService
from app.services.facts.fact_extractor import FactExtractor
from app.services.facts.evidence_persistence import EvidencePersistenceService
from app.services.mining.entity_extractor import MiningEntityExtractor
from app.services.mining.period_normalizer import PeriodNormalizer


class DocumentProcessor:
    @classmethod
    def log_stage(cls, db: Session, doc_id: str, stage: str, message: str, level: str = "INFO"):
        log_entry = ProcessingLog(
            document_id=doc_id,
            stage=stage,
            level=level,
            message=message,
            timestamp=datetime.now(timezone.utc)
        )
        db.add(log_entry)
        db.commit()
        logger.info(f"[{doc_id}][{stage}] {message}")

    @classmethod
    def process_document(cls, db: Session, document_id: str) -> Document:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise ValueError(f"Document {document_id} not found")

        file_path = doc.storage_path
        if not os.path.exists(file_path):
            doc.status = DocumentStatus.FAILED.value
            doc.processing_error = f"File not found on disk at {file_path}"
            db.commit()
            return doc

        cls.log_stage(db, doc.id, "INITIALIZATION", f"Starting document processing for {doc.original_filename} ({doc.file_type})")
        warnings_encountered = []

        try:
            # -------------------------------------------------------------
            # Stage 1: File Classification & Mining Category
            # -------------------------------------------------------------
            doc.status = DocumentStatus.CLASSIFYING.value
            doc.processing_progress = 10
            db.commit()

            file_type = doc.file_type
            doc_category = FileClassifier.classify_document_category(doc.original_filename, "")
            doc.document_category = doc_category
            doc.source_type = FileClassifier.classify_source_type(file_type, is_scanned=False).value
            cls.log_stage(db, doc.id, "CLASSIFICATION", f"Classified source type: {doc.source_type}, category: {doc_category}")

            # -------------------------------------------------------------
            # Stage 2: Quality Check & Pre-processing Dispatch
            # -------------------------------------------------------------
            doc.status = DocumentStatus.QUALITY_CHECK.value
            doc.processing_progress = 20
            db.commit()

            quality_score = 1.0
            quality_label = "EXCELLENT"
            quality_profile: Dict[str, Any] = {}
            enhancement_applied = False
            enhancement_methods = []
            quality_score_before = 1.0
            quality_score_after = 1.0
            ocr_conf_before = None
            ocr_conf_after = None

            extracted_text = ""
            extracted_tables = []
            extracted_pages = []
            extracted_sheets = []

            is_image = file_type in (FileType.PNG.value, FileType.JPG.value, FileType.JPEG.value, "PNG", "JPG", "JPEG")
            is_pdf = file_type in (FileType.PDF.value, "PDF")

            if is_image:
                with open(file_path, "rb") as f:
                    img_bytes = f.read()

                quality_profile = QualityAssessmentService.assess_image_data(img_bytes)
                quality_score_before = quality_profile["quality_score"]
                quality_score = quality_score_before
                quality_label = quality_profile["quality_label"]
                cls.log_stage(db, doc.id, "QUALITY_CHECK", f"Initial image quality score: {quality_score} ({quality_label})")

                # Stage 3: Enhancement if recommended
                if quality_profile.get("enhancement_recommended", False):
                    doc.status = DocumentStatus.ENHANCING.value
                    doc.processing_progress = 25
                    db.commit()

                    enhanced_bytes, ops = DocumentEnhancementService.enhance_image(
                        img_bytes,
                        deskew=True,
                        denoise=True,
                        enhance_contrast=True,
                        sharpen=True,
                        rotation_correction=quality_profile.get("orientation_correction", 0)
                    )
                    if ops:
                        enhancement_applied = True
                        enhancement_methods = ops
                        after_profile = QualityAssessmentService.assess_image_data(enhanced_bytes)
                        quality_score_after = after_profile["quality_score"]
                        quality_score = quality_score_after
                        quality_label = after_profile["quality_label"]
                        cls.log_stage(db, doc.id, "ENHANCING", f"Enhancements applied: {', '.join(ops)} (Quality {quality_score_before} -> {quality_score_after})")
                else:
                    cls.log_stage(db, doc.id, "QUALITY_CHECK", "Source quality sufficient — no enhancement required.")

                # Stage 4: OCR & Extraction
                if ocr_provider.is_available():
                    doc.status = DocumentStatus.OCR.value
                    doc.processing_progress = 35
                    db.commit()
                else:
                    doc.status = DocumentStatus.EXTRACTING.value
                    cls.log_stage(db, doc.id, "OCR", "OCR engine not available on host system. Proceeding with best effort.", level="WARNING")
                    warnings_encountered.append("OCR engine unavailable")

                img_res = ImageExtractor.extract(file_path)
                extracted_pages = img_res["pages"]
                extracted_tables = img_res["tables"]
                extracted_text = img_res["text"]
                ocr_conf_after = img_res.get("ocr_confidence")

            elif is_pdf:
                doc.status = DocumentStatus.EXTRACTING.value
                doc.processing_progress = 30
                db.commit()

                pdf_res = PDFExtractor.extract(file_path)
                extracted_pages = pdf_res["pages"]
                extracted_tables = pdf_res["tables"]
                extracted_text = pdf_res["text"]
                doc.page_count = pdf_res["page_count"]

                if pdf_res["is_scanned"]:
                    doc.source_type = FileClassifier.classify_source_type(FileType.PDF, is_scanned=True).value
                    quality_score = 0.75
                    quality_label = "FAIR"
                    cls.log_stage(db, doc.id, "QUALITY_CHECK", "Scanned PDF detected. Processed via page-level OCR/enhancement.")
                else:
                    quality_score = 0.95
                    quality_label = "EXCELLENT"
                    cls.log_stage(db, doc.id, "QUALITY_CHECK", "Digital PDF detected with native text stream.")

            elif file_type in (FileType.XLSX.value, FileType.XLS.value, "XLSX", "XLS"):
                doc.status = DocumentStatus.EXTRACTING.value
                doc.processing_progress = 30
                db.commit()

                excel_res = ExcelExtractor.extract(file_path)
                extracted_sheets = excel_res["sheets"]
                extracted_tables = excel_res["tables"]
                extracted_text = excel_res["text"]
                doc.sheet_count = len(extracted_sheets)

                total_rows = sum(s.get("row_count", 0) for s in extracted_sheets)
                total_cols = max([s.get("column_count", 0) for s in extracted_sheets] + [1])
                struct_q = QualityAssessmentService.assess_structured_data(total_rows, total_cols)
                quality_score = struct_q["quality_score"]
                quality_label = struct_q["quality_label"]
                cls.log_stage(db, doc.id, "EXTRACTING", f"Excel workbook processed: {len(extracted_sheets)} sheets, {total_rows} rows analyzed")

            elif file_type in (FileType.CSV.value, "CSV"):
                doc.status = DocumentStatus.EXTRACTING.value
                doc.processing_progress = 30
                db.commit()

                csv_res = CSVExtractor.extract(file_path)
                extracted_tables = csv_res["tables"]
                extracted_text = csv_res["text"]
                struct_q = QualityAssessmentService.assess_structured_data(csv_res["row_count"], csv_res["column_count"])
                quality_score = struct_q["quality_score"]
                quality_label = struct_q["quality_label"]
                cls.log_stage(db, doc.id, "EXTRACTING", f"CSV processed: {csv_res['row_count']} rows, encoding: {csv_res['encoding']}")

            elif file_type in (FileType.TXT.value, "TXT"):
                doc.status = DocumentStatus.EXTRACTING.value
                doc.processing_progress = 30
                db.commit()

                txt_res = TXTExtractor.extract(file_path)
                extracted_text = txt_res["text"]
                extracted_pages = txt_res["pages"]
                txt_q = QualityAssessmentService.assess_text_data(txt_res["total_chars"])
                quality_score = txt_q["quality_score"]
                quality_label = txt_q["quality_label"]
                cls.log_stage(db, doc.id, "EXTRACTING", f"Text file extracted: {txt_res['total_chars']} characters")

            # -------------------------------------------------------------
            # Stage 5: Save Quality Record
            # -------------------------------------------------------------
            doc.quality_label = quality_label
            quality_record = db.query(DocumentQuality).filter(DocumentQuality.document_id == doc.id).first()
            if not quality_record:
                quality_record = DocumentQuality(
                    document_id=doc.id,
                    quality_score=quality_score,
                    quality_label=quality_label,
                    enhancement_recommended=quality_profile.get("enhancement_recommended", False),
                    enhancement_applied=enhancement_applied,
                    enhancement_methods=", ".join(enhancement_methods) if enhancement_methods else None,
                    blur_level=quality_profile.get("blur_level"),
                    contrast_level=quality_profile.get("contrast_level"),
                    noise_level=quality_profile.get("noise_level"),
                    skew_angle=quality_profile.get("skew_angle"),
                    detected_dpi=quality_profile.get("detected_dpi"),
                    orientation_correction=quality_profile.get("orientation_correction"),
                    quality_score_before=quality_score_before,
                    quality_score_after=quality_score_after,
                    ocr_confidence_before=ocr_conf_before,
                    ocr_confidence_after=ocr_conf_after,
                    original_path=file_path
                )
                db.add(quality_record)
            else:
                quality_record.quality_score = quality_score
                quality_record.quality_label = quality_label
                quality_record.enhancement_applied = enhancement_applied
                quality_record.enhancement_methods = ", ".join(enhancement_methods) if enhancement_methods else None

            # -------------------------------------------------------------
            # Stage 6: Persist Document Pages, Sheets, and Tables
            # -------------------------------------------------------------
            doc.status = DocumentStatus.TABLE_PROCESSING.value
            doc.processing_progress = 50
            db.commit()

            # Clean previous child records
            db.query(DocumentPage).filter(DocumentPage.document_id == doc.id).delete()
            db.query(DocumentSheet).filter(DocumentSheet.document_id == doc.id).delete()
            db.query(DocumentTable).filter(DocumentTable.document_id == doc.id).delete()
            db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).delete()
            db.flush()

            for p in extracted_pages:
                doc_page = DocumentPage(
                    document_id=doc.id,
                    page_number=p["page_number"],
                    raw_text=p.get("text", ""),
                    char_count=p.get("char_count", 0),
                    word_count=len((p.get("text") or "").split()),
                    has_native_text=p.get("has_native_text", True),
                    is_ocr_page=p.get("ocr_applied", False),
                    ocr_confidence=p.get("ocr_confidence")
                )
                db.add(doc_page)

            created_sheets_map = {}
            for s in extracted_sheets:
                doc_sheet = DocumentSheet(
                    document_id=doc.id,
                    sheet_name=s["sheet_name"],
                    sheet_index=s["sheet_index"],
                    row_count=s.get("row_count", 0),
                    col_count=s.get("column_count", 0),
                    used_range=s.get("used_range"),
                    header_row=s.get("header_row"),
                    has_merged_cells=s.get("has_merged_cells", False),
                )
                db.add(doc_sheet)
                db.flush()
                created_sheets_map[s["sheet_name"]] = doc_sheet.id

            for t in extracted_tables:
                sheet_id = created_sheets_map.get(t.get("sheet_name"))
                doc_table = DocumentTable(
                    document_id=doc.id,
                    sheet_id=sheet_id,
                    table_index=t.get("table_index", 0),
                    source_type=str(file_type),
                    page_number=t.get("page_number"),
                    sheet_name=t.get("sheet_name"),
                    source_range=t.get("source_range"),
                    row_count=t.get("row_count", 0),
                    col_count=t.get("column_count", 0),
                    headers_json=json.dumps(t.get("headers", [])),
                    data_json=json.dumps(t.get("data", [])[:250]),
                    confidence=t.get("confidence", 0.95),
                    structure_status=t.get("structure_status", "CLEAN")
                )
                db.add(doc_table)

            doc.table_count = len(extracted_tables)
            cls.log_stage(db, doc.id, "TABLE_PROCESSING", f"Structured {len(extracted_pages)} pages, {len(extracted_sheets)} sheets, and {len(extracted_tables)} tables")

            # -------------------------------------------------------------
            # Stage 7: Semantic Chunking (Index Preparation)
            # -------------------------------------------------------------
            doc.status = DocumentStatus.INDEX_PREPARATION.value
            doc.processing_progress = 65
            db.commit()

            chunks_data = []
            if extracted_pages:
                for p in extracted_pages:
                    c_list = ChunkingService.chunk_text(
                        text=p.get("text", ""),
                        chunk_size=1000,
                        chunk_overlap=150,
                        page_number=p["page_number"],
                        section=f"Page {p['page_number']}",
                        document_id=doc.id,
                        base_index=len(chunks_data)
                    )
                    chunks_data.extend(c_list)
            else:
                chunks_data = ChunkingService.chunk_text(
                    text=extracted_text,
                    chunk_size=1000,
                    chunk_overlap=150,
                    document_id=doc.id
                )

            for c in chunks_data:
                chunk_obj = DocumentChunk(
                    document_id=doc.id,
                    chunk_index=c["chunk_index"],
                    content=c["content"],
                    token_count=c["char_count"] // 4,
                    page_number=c.get("page_number"),
                    section=c.get("section")
                )
                db.add(chunk_obj)

            cls.log_stage(db, doc.id, "INDEX_PREPARATION", f"Created {len(chunks_data)} semantic chunks for downstream search")

            # -------------------------------------------------------------
            # Stage 8: Deterministic Fact Extraction & Normalization
            # -------------------------------------------------------------
            doc.status = DocumentStatus.FACT_EXTRACTION.value
            doc.processing_progress = 75
            db.commit()

            global_entities = MiningEntityExtractor.extract_entities_from_text(
                f"{doc.original_filename}\n{extracted_text[:3000]}"
            )
            # Extract reporting period if detectable
            detected_period = PeriodNormalizer.extract_period(doc.original_filename) or global_entities.get("period")
            if detected_period and not doc.reporting_period:
                doc.reporting_period = detected_period

            table_facts = FactExtractor.extract_from_tables(
                tables=extracted_tables,
                document_id=doc.id,
                doc_category=doc_category,
                doc_quality_score=quality_score,
                global_context_entities=global_entities
            )

            text_facts = []
            if extracted_pages:
                for p in extracted_pages:
                    tf = FactExtractor.extract_from_text(
                        text=p.get("text", ""),
                        document_id=doc.id,
                        page_number=p["page_number"],
                        doc_quality_score=quality_score,
                        global_context_entities=global_entities
                    )
                    text_facts.extend(tf)
            else:
                text_facts = FactExtractor.extract_from_text(
                    text=extracted_text,
                    document_id=doc.id,
                    doc_quality_score=quality_score,
                    global_context_entities=global_entities
                )

            all_extracted_facts = table_facts + text_facts
            cls.log_stage(db, doc.id, "FACT_EXTRACTION", f"Identified {len(all_extracted_facts)} candidate facts ({len(table_facts)} from tables, {len(text_facts)} from text)")

            # -------------------------------------------------------------
            # Stage 9: Normalizing & Evidence Persistence
            # -------------------------------------------------------------
            doc.status = DocumentStatus.NORMALIZING.value
            doc.processing_progress = 85
            db.commit()

            doc.status = DocumentStatus.STORING_EVIDENCE.value
            doc.processing_progress = 90
            db.commit()

            saved_facts = EvidencePersistenceService.persist_facts(db, doc.id, all_extracted_facts)
            doc.fact_count = len(saved_facts)
            cls.log_stage(db, doc.id, "STORING_EVIDENCE", f"Successfully recorded {len(saved_facts)} facts with provenance into Evidence Ledger")

            # -------------------------------------------------------------
            # Stage 10: Completion
            # -------------------------------------------------------------
            if warnings_encountered and len(warnings_encountered) > 0 and doc.fact_count == 0:
                doc.status = DocumentStatus.COMPLETED_WITH_WARNINGS.value
                doc.processing_message = f"Completed with warnings: {'; '.join(warnings_encountered)}"
            else:
                doc.status = DocumentStatus.READY.value
                doc.processing_message = f"Processing complete. {doc.fact_count} facts extracted."

            doc.processing_progress = 100
            doc.processing_error = None
            doc.processed_at = datetime.now(timezone.utc)

            audit = AuditEvent(
                action=AuditAction.DOCUMENT_PROCESSED.value,
                entity_type="DOCUMENT",
                entity_id=doc.id,
                user="MineIntel Pipeline",
                details=f"Pipeline completed: {doc.fact_count} facts, {doc.table_count} tables, {len(chunks_data)} chunks, status: {doc.status}"
            )
            db.add(audit)
            db.commit()

            cls.log_stage(db, doc.id, "COMPLETION", f"Pipeline completed. Final status: {doc.status}.")
            return doc

        except Exception as exc:
            db.rollback()
            err_trace = traceback.format_exc()
            logger.error(f"Processing failed for document {doc.id}: {err_trace}")
            doc.status = DocumentStatus.FAILED.value
            doc.processing_error = str(exc)
            doc.processing_message = f"Error: {str(exc)[:100]}"
            db.commit()
            cls.log_stage(db, doc.id, "FAILURE", f"Processing error: {str(exc)}", level="ERROR")
            return doc

    @classmethod
    def reprocess_document(cls, db: Session, document_id: str) -> Document:
        """
        Clears previous extraction artifacts and re-runs the entire pipeline.
        Avoids duplicate facts and ensures idempotency.
        """
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise ValueError(f"Document {document_id} not found")

        # Delete old child records
        db.query(ExtractedFact).filter(ExtractedFact.document_id == document_id).delete()
        db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()
        db.query(DocumentTable).filter(DocumentTable.document_id == document_id).delete()
        db.query(DocumentSheet).filter(DocumentSheet.document_id == document_id).delete()
        db.query(DocumentPage).filter(DocumentPage.document_id == document_id).delete()
        db.query(DocumentQuality).filter(DocumentQuality.document_id == document_id).delete()
        db.query(ProcessingLog).filter(ProcessingLog.document_id == document_id).delete()

        doc.status = DocumentStatus.UPLOADED.value
        doc.processing_progress = 0
        doc.fact_count = 0
        doc.table_count = 0
        doc.page_count = 0
        doc.sheet_count = 0
        doc.average_confidence = None
        doc.processing_error = None
        doc.processing_message = "Reprocessing initiated"
        db.commit()

        cls.log_stage(db, doc.id, "REPROCESS", f"Reprocessing triggered for {doc.original_filename}")
        return cls.process_document(db, document_id)
