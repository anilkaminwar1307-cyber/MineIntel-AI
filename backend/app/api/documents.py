import os
import asyncio
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query, BackgroundTasks, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.models.document import Document, DocumentChunk
from app.models.processing import DocumentPage, DocumentSheet, DocumentTable, DocumentQuality, ProcessingLog
from app.models.fact import ExtractedFact
from app.models.validation import EvidenceConflict
from app.models.enums import DocumentStatus, AuditAction
from app.schemas.document import (
    DocumentResponse, DocumentListResponse, DocumentUploadResponse,
    DocumentPageResponse, DocumentSheetResponse, DocumentTableResponse,
    DocumentChunkResponse, DocumentQualityResponse, ProcessingLogResponse,
    BatchUploadResponse, BatchUploadItemResult, ProcessingStatusResponse,
    ExtractionSummaryResponse, SourcePreviewResponse, SourcePreviewPage,
    SourcePreviewSheet, MetadataUpdateRequest, DocumentValidationsResponse,
    DocumentValidationIssueItem, DocumentConflictItem
)
from app.schemas.fact import ExtractedFactResponse
from app.services.storage.local import storage_service
from app.services.audit import log_audit_event
from app.services.pipeline.document_processor import DocumentProcessor
from app.core.logging import logger

router = APIRouter(prefix="/documents", tags=["Documents"])


def _infer_category(current_category: str, filename_lower: str) -> str:
    """Heuristic category inference from filename."""
    if current_category != "General Mining Report":
        return current_category
    if "drill" in filename_lower:
        return "Drilling & Exploration"
    if "prod" in filename_lower:
        return "Production Report"
    if "dispatch" in filename_lower:
        return "Dispatch Statement"
    if "geol" in filename_lower:
        return "Geological Assessment"
    if "reserve" in filename_lower:
        return "Reserve Estimation"
    return current_category


@router.get("", response_model=DocumentListResponse)
def list_documents(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    status_filter: Optional[str] = None,
    category: Optional[str] = None,
    organization: Optional[str] = None
):
    """
    List all uploaded documents with pagination, text search, and category/status filtering.
    """
    query = db.query(Document)

    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(Document.original_filename.ilike(search_pattern))

    if status_filter:
        query = query.filter(Document.status == status_filter)

    if category:
        query = query.filter(Document.document_category == category)

    if organization:
        query = query.filter(Document.organization == organization)

    total = query.count()
    offset = (page - 1) * page_size
    items = query.order_by(desc(Document.created_at)).offset(offset).limit(page_size).all()

    return DocumentListResponse(
        items=[DocumentResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    document_category: Optional[str] = Form("General Mining Report"),
    reporting_period: Optional[str] = Form(None),
    organization: Optional[str] = Form("CMPDI / CIL"),
    auto_process: bool = Form(False),
    db: Session = Depends(get_db)
):
    """
    Uploads a mining/geological document.
    Validates file extension and size, saves file safely to disk, records document in database,
    triggers the Phase 2 intelligence pipeline, and writes an audit event.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename missing in upload request.")

    # 1. Save to disk with security sanitation & validation
    stored_filename, storage_path, file_size, file_type, sha256_hash = await storage_service.save_file(file)

    # 2. SHA-256 duplicate detection
    existing_doc = None
    if sha256_hash:
        existing_doc = db.query(Document).filter(Document.sha256 == sha256_hash, Document.is_latest_version == True).first()

    # 3. Infer category from filename
    inferred_category = _infer_category(document_category or "General Mining Report", file.filename.lower())

    # 4. Create Document DB entry
    document = Document(
        original_filename=file.filename,
        stored_filename=stored_filename,
        file_type=file_type.value if hasattr(file_type, 'value') else str(file_type),
        mime_type=file.content_type or "application/octet-stream",
        file_size=file_size,
        document_category=inferred_category,
        organization=organization or "CMPDI / CIL",
        reporting_period=reporting_period,
        storage_path=storage_path,
        sha256=sha256_hash,
        page_count=0,
        sheet_count=0,
        status=DocumentStatus.UPLOADED.value,
        processing_progress=0,
        processing_message="Uploaded successfully. Ready for processing.",
        fact_count=0,
        topic_count=0,
        is_demo=False
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    # 5. Create Audit Log
    log_audit_event(
        db=db,
        action=AuditAction.DOCUMENT_UPLOADED,
        entity_type="DOCUMENT",
        entity_id=document.id,
        user="CMPDI Analyst",
        details=f"Uploaded '{document.original_filename}' ({file_type.value if hasattr(file_type, 'value') else file_type}, {file_size} bytes)"
    )

    logger.info(f"Document created in DB: id={document.id}, name={document.original_filename}")

    # 6. Process document through Phase 2 pipeline if auto_process is enabled
    if auto_process:
        try:
            document = DocumentProcessor.process_document(db, document.id)
        except Exception as e:
            logger.error(f"Auto-processing failed: {e}")

    return DocumentUploadResponse(
        message=f"Document '{document.original_filename}' uploaded and processed successfully.",
        document=DocumentResponse.model_validate(document),
        is_duplicate=existing_doc is not None,
        existing_document=DocumentResponse.model_validate(existing_doc) if existing_doc else None
    )


@router.post("/batch-upload", response_model=BatchUploadResponse, status_code=status.HTTP_201_CREATED)
async def batch_upload_documents(
    files: List[UploadFile] = File(...),
    document_category: Optional[str] = Form("General Mining Report"),
    reporting_period: Optional[str] = Form(None),
    organization: Optional[str] = Form("CMPDI / CIL"),
    auto_process: bool = Form(True),
    db: Session = Depends(get_db)
):
    """
    Batch upload 1-10 mining documents in a single request.
    Each file is individually SHA-256 fingerprinted, deduplicated, stored, and optionally auto-processed.
    Returns a per-file result summary.
    """
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Batch upload is limited to 10 files per request.")
    if len(files) == 0:
        raise HTTPException(status_code=400, detail="No files provided in batch upload request.")

    results: List[BatchUploadItemResult] = []
    successful = 0
    duplicates = 0
    failed = 0

    for file in files:
        item_warnings: List[str] = []
        if not file.filename:
            results.append(BatchUploadItemResult(
                filename="unknown", file_type="", file_size=0,
                status="FAILED", error="Missing filename"
            ))
            failed += 1
            continue

        try:
            stored_filename, storage_path, file_size, file_type, sha256_hash = await storage_service.save_file(file)

            dup_doc = None
            is_dup = False
            if sha256_hash:
                dup_doc = db.query(Document).filter(
                    Document.sha256 == sha256_hash,
                    Document.is_latest_version == True
                ).first()
                if dup_doc:
                    is_dup = True
                    duplicates += 1
                    item_warnings.append(f"Duplicate of existing document '{dup_doc.original_filename}'")

            inferred_category = _infer_category(
                document_category or "General Mining Report", file.filename.lower()
            )

            doc = Document(
                original_filename=file.filename,
                stored_filename=stored_filename,
                file_type=file_type.value if hasattr(file_type, 'value') else str(file_type),
                mime_type=file.content_type or "application/octet-stream",
                file_size=file_size,
                document_category=inferred_category,
                organization=organization or "CMPDI / CIL",
                reporting_period=reporting_period,
                storage_path=storage_path,
                sha256=sha256_hash,
                page_count=0, sheet_count=0,
                status=DocumentStatus.UPLOADED.value,
                processing_progress=0,
                processing_message="Batch uploaded. Ready for processing.",
                fact_count=0, topic_count=0,
                is_demo=False
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)

            log_audit_event(
                db=db,
                action=AuditAction.DOCUMENT_UPLOADED,
                entity_type="DOCUMENT",
                entity_id=doc.id,
                user="CMPDI Analyst",
                details=f"Batch uploaded '{doc.original_filename}' ({doc.file_type}, {file_size} bytes)"
            )

            facts_extracted = 0
            if auto_process and not is_dup:
                try:
                    processed = DocumentProcessor.process_document(db, doc.id)
                    facts_extracted = processed.fact_count
                except Exception as pe:
                    item_warnings.append(f"Pipeline warning: {str(pe)[:80]}")
                    logger.error(f"Batch pipeline error for {file.filename}: {pe}")

            successful += 1
            results.append(BatchUploadItemResult(
                filename=file.filename,
                file_type=doc.file_type,
                file_size=file_size,
                status=doc.status,
                document_id=doc.id,
                is_duplicate=is_dup,
                duplicate_of_id=dup_doc.id if dup_doc else None,
                duplicate_of_filename=dup_doc.original_filename if dup_doc else None,
                detected_organization=doc.organization,
                detected_period=doc.reporting_period,
                facts_extracted=facts_extracted,
                warnings=item_warnings
            ))

        except Exception as e:
            failed += 1
            logger.error(f"Batch upload error for {file.filename}: {e}")
            results.append(BatchUploadItemResult(
                filename=file.filename,
                file_type="",
                file_size=0,
                status="FAILED",
                error=str(e)[:200]
            ))

    return BatchUploadResponse(
        total_files=len(files),
        successful=successful,
        duplicates=duplicates,
        failed=failed,
        items=results
    )


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: str, db: Session = Depends(get_db)):
    """Retrieve document metadata by document ID."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document with ID '{document_id}' not found.")
    return DocumentResponse.model_validate(doc)


@router.get("/{document_id}/status", response_model=ProcessingStatusResponse)
def get_document_status(document_id: str, db: Session = Depends(get_db)):
    """Retrieve granular processing status, stage, and warning count for a document."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document with ID '{document_id}' not found.")

    # Fetch the latest processing log stage
    latest_log = (
        db.query(ProcessingLog)
        .filter(ProcessingLog.document_id == document_id)
        .order_by(desc(ProcessingLog.timestamp))
        .first()
    )
    warning_logs = (
        db.query(ProcessingLog)
        .filter(ProcessingLog.document_id == document_id, ProcessingLog.level == "WARNING")
        .all()
    )
    return ProcessingStatusResponse(
        document_id=doc.id,
        status=doc.status,
        processing_progress=doc.processing_progress,
        processing_message=doc.processing_message,
        current_stage=latest_log.stage if latest_log else None,
        fact_count=doc.fact_count,
        warning_count=len(warning_logs),
        warnings=[w.message for w in warning_logs],
        processing_error=doc.processing_error,
        processing_started_at=doc.processing_started_at,
        processing_completed_at=doc.processing_completed_at
    )


@router.get("/{document_id}/extraction-summary", response_model=ExtractionSummaryResponse)
def get_extraction_summary(document_id: str, db: Session = Depends(get_db)):
    """Return a post-processing summary: fact count, quality, conflicts, and pipeline duration."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document with ID '{document_id}' not found.")

    quality = db.query(DocumentQuality).filter(DocumentQuality.document_id == document_id).first()
    high_conf = db.query(ExtractedFact).filter(
        ExtractedFact.document_id == document_id,
        ExtractedFact.confidence_score >= 0.85
    ).count()
    needs_review = db.query(ExtractedFact).filter(
        ExtractedFact.document_id == document_id,
        ExtractedFact.validation_status == "NEEDS_REVIEW"
    ).count()
    conflict_count = db.query(EvidenceConflict).filter(
        EvidenceConflict.primary_fact_id.in_(
            db.query(ExtractedFact.id).filter(ExtractedFact.document_id == document_id)
        )
    ).count()
    warning_logs = db.query(ProcessingLog).filter(
        ProcessingLog.document_id == document_id, ProcessingLog.level == "WARNING"
    ).all()

    duration_seconds = None
    if doc.processing_started_at and doc.processing_completed_at:
        duration_seconds = (doc.processing_completed_at - doc.processing_started_at).total_seconds()

    return ExtractionSummaryResponse(
        document_id=doc.id,
        original_filename=doc.original_filename,
        file_type=doc.file_type,
        document_category=doc.document_category,
        organization=doc.organization,
        reporting_period=doc.reporting_period,
        quality_label=doc.quality_label,
        quality_score=quality.quality_score if quality else None,
        page_count=doc.page_count,
        sheet_count=doc.sheet_count,
        table_count=doc.table_count,
        total_facts=doc.fact_count,
        high_confidence_facts=high_conf,
        needs_review_facts=needs_review,
        conflicts_count=conflict_count,
        warning_count=len(warning_logs),
        warnings=[w.message for w in warning_logs],
        is_demo=doc.is_demo,
        duration_seconds=duration_seconds
    )


@router.get("/{document_id}/source-preview", response_model=SourcePreviewResponse)
def get_source_preview(document_id: str, db: Session = Depends(get_db)):
    """
    Returns a lightweight preview of the raw source: first 3 pages (text PDFs),
    first 3 sheets with sample rows (Excel), or plain text snippet (CSV/TXT).
    """
    import json as _json
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document with ID '{document_id}' not found.")

    pages: List[SourcePreviewPage] = []
    sheets: List[SourcePreviewSheet] = []
    text_preview: Optional[str] = None

    if doc.file_type in ("PDF",):
        db_pages = (
            db.query(DocumentPage)
            .filter(DocumentPage.document_id == document_id)
            .order_by(DocumentPage.page_number)
            .limit(5)
            .all()
        )
        for p in db_pages:
            pages.append(SourcePreviewPage(
                page_number=p.page_number,
                raw_text=(p.raw_text or "")[:2000],
                has_native_text=p.has_native_text,
                is_ocr_page=p.is_ocr_page,
                ocr_confidence=p.ocr_confidence,
                extraction_method=p.extraction_method
            ))

    elif doc.file_type in ("XLSX", "XLS"):
        db_sheets = (
            db.query(DocumentSheet)
            .filter(DocumentSheet.document_id == document_id)
            .order_by(DocumentSheet.sheet_index)
            .limit(3)
            .all()
        )
        for s in db_sheets:
            table = (
                db.query(DocumentTable)
                .filter(
                    DocumentTable.document_id == document_id,
                    DocumentTable.sheet_name == s.sheet_name
                )
                .first()
            )
            headers = []
            rows = []
            if table and table.headers_json:
                try:
                    headers = _json.loads(table.headers_json)
                except Exception:
                    headers = []
            if table and table.data_json:
                try:
                    rows = _json.loads(table.data_json)[:10]
                except Exception:
                    rows = []
            sheets.append(SourcePreviewSheet(
                sheet_name=s.sheet_name,
                used_range=s.used_range,
                headers=headers,
                rows=rows,
                row_count=s.row_count,
                col_count=s.col_count
            ))

    else:
        # CSV / TXT — just show the first chunk's text
        chunk = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
            .first()
        )
        text_preview = (chunk.content[:3000] if chunk else None)

    return SourcePreviewResponse(
        document_id=doc.id,
        original_filename=doc.original_filename,
        file_type=doc.file_type,
        pages=pages,
        sheets=sheets,
        text_preview=text_preview
    )


@router.patch("/{document_id}/metadata", response_model=DocumentResponse)
def update_document_metadata(
    document_id: str,
    payload: MetadataUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update document metadata (category, organization, reporting period) without re-processing."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document with ID '{document_id}' not found.")

    if payload.document_category is not None:
        doc.document_category = payload.document_category
    if payload.organization is not None:
        doc.organization = payload.organization
    if payload.reporting_period is not None:
        doc.reporting_period = payload.reporting_period

    db.commit()
    db.refresh(doc)

    log_audit_event(
        db=db,
        action=AuditAction.FACT_EDITED,
        entity_type="DOCUMENT",
        entity_id=doc.id,
        user="CMPDI Analyst",
        details=f"Metadata updated for '{doc.original_filename}'"
    )
    return DocumentResponse.model_validate(doc)


@router.post("/{document_id}/process", response_model=DocumentResponse)
def process_document_endpoint(document_id: str, db: Session = Depends(get_db)):
    """Trigger the full Document Intelligence Pipeline on an uploaded document."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document with ID '{document_id}' not found.")

    processed_doc = DocumentProcessor.process_document(db, document_id)
    return DocumentResponse.model_validate(processed_doc)


@router.post("/{document_id}/reprocess", response_model=DocumentResponse)
def reprocess_document_endpoint(document_id: str, db: Session = Depends(get_db)):
    """Re-run the extraction pipeline, clearing old records and cleanly rebuilding facts."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document with ID '{document_id}' not found.")

    processed_doc = DocumentProcessor.reprocess_document(db, document_id)
    return DocumentResponse.model_validate(processed_doc)


@router.get("/{document_id}/pages", response_model=List[DocumentPageResponse])
def get_document_pages(document_id: str, db: Session = Depends(get_db)):
    """Retrieve all extracted pages for a document."""
    pages = db.query(DocumentPage).filter(DocumentPage.document_id == document_id).order_by(DocumentPage.page_number).all()
    return [DocumentPageResponse.model_validate(p) for p in pages]


@router.get("/{document_id}/sheets", response_model=List[DocumentSheetResponse])
def get_document_sheets(document_id: str, db: Session = Depends(get_db)):
    """Retrieve all worksheets for an Excel document."""
    sheets = db.query(DocumentSheet).filter(DocumentSheet.document_id == document_id).order_by(DocumentSheet.sheet_index).all()
    return [DocumentSheetResponse.model_validate(s) for s in sheets]


@router.get("/{document_id}/tables", response_model=List[DocumentTableResponse])
def get_document_tables(document_id: str, db: Session = Depends(get_db)):
    """Retrieve all extracted tabular blocks for a document."""
    tables = db.query(DocumentTable).filter(DocumentTable.document_id == document_id).order_by(DocumentTable.table_index).all()
    return [DocumentTableResponse.model_validate(t) for t in tables]


@router.get("/{document_id}/chunks", response_model=List[DocumentChunkResponse])
def get_document_chunks(document_id: str, db: Session = Depends(get_db)):
    """Retrieve all semantic chunks for a document."""
    chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).order_by(DocumentChunk.chunk_index).all()
    return [DocumentChunkResponse.model_validate(c) for c in chunks]


@router.get("/{document_id}/facts", response_model=List[ExtractedFactResponse])
def get_document_facts(document_id: str, db: Session = Depends(get_db)):
    """Retrieve all extracted facts originating from this document."""
    facts = db.query(ExtractedFact).filter(ExtractedFact.document_id == document_id).order_by(ExtractedFact.created_at).all()
    return [ExtractedFactResponse.model_validate(f) for f in facts]


@router.get("/{document_id}/quality", response_model=Optional[DocumentQualityResponse])
def get_document_quality(document_id: str, db: Session = Depends(get_db)):
    """Retrieve quality assessment profile for a document."""
    quality = db.query(DocumentQuality).filter(DocumentQuality.document_id == document_id).first()
    if not quality:
        return None
    return DocumentQualityResponse.model_validate(quality)


@router.get("/{document_id}/processing-log", response_model=List[ProcessingLogResponse])
def get_document_processing_log(document_id: str, db: Session = Depends(get_db)):
    """Retrieve timestamped pipeline processing logs for a document."""
    logs = db.query(ProcessingLog).filter(ProcessingLog.document_id == document_id).order_by(ProcessingLog.timestamp).all()
    return [ProcessingLogResponse.model_validate(l) for l in logs]


@router.get("/{document_id}/validations", response_model=DocumentValidationsResponse)
def get_document_validations(document_id: str, db: Session = Depends(get_db)):
    """Retrieve validation issues and cross-document conflicts for this specific document."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document with ID '{document_id}' not found.")

    issues = (
        db.query(ValidationIssue)
        .filter(ValidationIssue.document_id == document_id)
        .order_by(desc(ValidationIssue.created_at))
        .all()
    )

    fact_ids = [iss.fact_id for iss in issues if iss.fact_id]
    facts_map = {}
    if fact_ids:
        facts = db.query(ExtractedFact).filter(ExtractedFact.id.in_(fact_ids)).all()
        facts_map = {f.id: f for f in facts}

    doc_fact_ids = [f.id for f in db.query(ExtractedFact.id).filter(ExtractedFact.document_id == document_id).all()]
    conflicts = []
    if doc_fact_ids:
        conflict_rows = (
            db.query(EvidenceConflict)
            .filter(
                (EvidenceConflict.primary_fact_id.in_(doc_fact_ids)) |
                (EvidenceConflict.conflicting_fact_id.in_(doc_fact_ids))
            )
            .order_by(desc(EvidenceConflict.created_at))
            .all()
        )
        c_fact_ids = []
        for c in conflict_rows:
            c_fact_ids.extend([c.primary_fact_id, c.conflicting_fact_id])
        c_facts_map = {f.id: f for f in db.query(ExtractedFact).filter(ExtractedFact.id.in_(c_fact_ids)).all()} if c_fact_ids else {}

        for c in conflict_rows:
            pf = c_facts_map.get(c.primary_fact_id)
            cf = c_facts_map.get(c.conflicting_fact_id)
            p_val = f"{pf.numeric_value} {pf.unit or ''}" if pf and pf.numeric_value is not None else None
            c_val = f"{cf.numeric_value} {cf.unit or ''}" if cf and cf.numeric_value is not None else None
            conflicts.append(DocumentConflictItem(
                id=c.id,
                metric_code=c.metric_code,
                primary_fact_id=c.primary_fact_id,
                conflicting_fact_id=c.conflicting_fact_id,
                description=c.description,
                discrepancy_percent=c.discrepancy_percent,
                status=c.status,
                created_at=c.created_at,
                primary_value=p_val,
                conflicting_value=c_val
            ))

    issue_items = []
    open_count = 0
    resolved_count = 0
    for iss in issues:
        if iss.is_resolved:
            resolved_count += 1
        else:
            open_count += 1
        f = facts_map.get(iss.fact_id)
        issue_items.append(DocumentValidationIssueItem(
            id=iss.id,
            document_id=iss.document_id,
            fact_id=iss.fact_id,
            issue_type=iss.issue_type,
            severity=iss.severity,
            description=iss.description,
            is_resolved=iss.is_resolved,
            created_at=iss.created_at,
            metric_name=f.metric_name if f else None,
            numeric_value=f.numeric_value if f else None,
            unit=f.unit if f else None,
            cell_reference=f.cell_reference if f else None,
            page_number=f.page_number if f else None
        ))

    return DocumentValidationsResponse(
        document_id=doc.id,
        total_issues=len(issues),
        open_issues=open_count,
        resolved_issues=resolved_count,
        conflicts_count=len(conflicts),
        issues=issue_items,
        conflicts=conflicts
    )


@router.delete("/{document_id}", status_code=status.HTTP_200_OK)
def delete_document(document_id: str, db: Session = Depends(get_db)):
    """
    Deletes a document from the database and removes its stored file on disk.
    Records an audit log entry.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document with ID '{document_id}' not found.")

    filename = doc.original_filename
    stored_name = doc.stored_filename

    # Delete disk file
    storage_service.delete_file(stored_name)

    # Delete DB row (cascades to chunks, facts, validation issues, pages, sheets, tables, quality, logs)
    db.delete(doc)
    db.commit()

    # Log audit event
    log_audit_event(
        db=db,
        action=AuditAction.DOCUMENT_DELETED,
        entity_type="DOCUMENT",
        entity_id=document_id,
        user="CMPDI Analyst",
        details=f"Deleted document '{filename}' (ID: {document_id})"
    )

    logger.info(f"Document deleted: id={document_id}, name={filename}")
    return {"message": f"Document '{filename}' deleted successfully.", "id": document_id}
