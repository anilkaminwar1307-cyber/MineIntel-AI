import os
from typing import Optional, List
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.models.document import Document, DocumentChunk
from app.models.processing import DocumentPage, DocumentSheet, DocumentTable, DocumentQuality, ProcessingLog
from app.models.fact import ExtractedFact
from app.models.enums import DocumentStatus, AuditAction
from app.schemas.document import (
    DocumentResponse, DocumentListResponse, DocumentUploadResponse,
    DocumentPageResponse, DocumentSheetResponse, DocumentTableResponse,
    DocumentChunkResponse, DocumentQualityResponse, ProcessingLogResponse
)
from app.schemas.fact import ExtractedFactResponse
from app.services.storage.local import storage_service
from app.services.audit import log_audit_event
from app.services.pipeline.document_processor import DocumentProcessor
from app.core.logging import logger

router = APIRouter(prefix="/documents", tags=["Documents"])


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
    stored_filename, storage_path, file_size, file_type = await storage_service.save_file(file)

    # 2. Derive simple category heuristic if default provided
    filename_lower = file.filename.lower()
    inferred_category = document_category
    if document_category == "General Mining Report":
        if "drill" in filename_lower:
            inferred_category = "Drilling & Exploration"
        elif "prod" in filename_lower:
            inferred_category = "Production Report"
        elif "dispatch" in filename_lower:
            inferred_category = "Dispatch Statement"
        elif "geol" in filename_lower:
            inferred_category = "Geological Assessment"
        elif "reserve" in filename_lower:
            inferred_category = "Reserve Estimation"

    # 3. Create Document DB entry
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
        page_count=0,
        sheet_count=0,
        status=DocumentStatus.UPLOADED.value,
        processing_progress=0,
        processing_message="Uploaded successfully. Ready for processing.",
        fact_count=0,
        topic_count=0
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    # 4. Create Audit Log
    log_audit_event(
        db=db,
        action=AuditAction.DOCUMENT_UPLOADED,
        entity_type="DOCUMENT",
        entity_id=document.id,
        user="CMPDI Analyst",
        details=f"Uploaded '{document.original_filename}' ({file_type.value}, {file_size} bytes)"
    )

    logger.info(f"Document created in DB: id={document.id}, name={document.original_filename}")

    # 5. Process document through Phase 2 pipeline if auto_process is enabled
    if auto_process:
        try:
            document = DocumentProcessor.process_document(db, document.id)
        except Exception as e:
            logger.error(f"Auto-processing failed: {e}")

    return DocumentUploadResponse(
        message=f"Document '{document.original_filename}' uploaded and processed successfully.",
        document=DocumentResponse.model_validate(document)
    )


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: str, db: Session = Depends(get_db)):
    """Retrieve document metadata by document ID."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document with ID '{document_id}' not found.")
    return DocumentResponse.model_validate(doc)


@router.get("/{document_id}/status")
def get_document_status(document_id: str, db: Session = Depends(get_db)):
    """Retrieve processing status and progress for a document."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document with ID '{document_id}' not found.")
    return {
        "id": doc.id,
        "original_filename": doc.original_filename,
        "status": doc.status,
        "processing_progress": doc.processing_progress,
        "processing_message": doc.processing_message,
        "processing_error": doc.processing_error,
        "fact_count": doc.fact_count,
        "table_count": doc.table_count,
        "page_count": doc.page_count,
        "sheet_count": doc.sheet_count,
        "quality_label": doc.quality_label,
        "average_confidence": doc.average_confidence,
        "processed_at": doc.processed_at
    }


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
