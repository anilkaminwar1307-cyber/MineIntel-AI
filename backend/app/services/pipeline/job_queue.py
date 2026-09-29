"""
Durable Document Processing Job Queue
─────────────────────────────────────
Manages persistent ProcessingJob records in SQLAlchemy.
Executes multi-stage ingestion pipeline asynchronously via thread pool
without blocking the FastAPI HTTP upload response or relying on external brokers.

Stages:
1. QUEUED (0%)
2. CLASSIFYING (15%)
3. EXTRACTING (30%)
4. OCR (50% if scanned)
5. TABLE_PROCESSING (65%)
6. FACT_EXTRACTION (80%)
7. NORMALIZING (90%)
8. VALIDATING & INDEXING (95%)
9. COMPLETED or REVIEW_REQUIRED (100%)
"""
import traceback
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.logging import logger
from app.models.document import Document
from app.models.review import ProcessingJob
from app.models.enums import DocumentStatus, JobStatus
from app.services.pipeline.document_processor import DocumentProcessor
from app.services.audit import log_audit_event
from app.models.enums import AuditAction

# Thread pool for asynchronous background document ingestion
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="mineintel_worker")


class DurableProcessingQueue:
    @staticmethod
    def create_job(
        db: Session,
        document_id: str,
        idempotency_key: Optional[str] = None,
        max_retries: int = 3
    ) -> ProcessingJob:
        """Create and persist a new job in QUEUED status."""
        # Check idempotency
        if idempotency_key:
            existing = db.query(ProcessingJob).filter(
                ProcessingJob.idempotency_key == idempotency_key,
                ProcessingJob.status.in_(["QUEUED", "PROCESSING"])
            ).first()
            if existing:
                logger.info(f"Returning existing idempotent job {existing.id} for doc {document_id}")
                return existing

        # Get current document version
        doc = db.query(Document).filter(Document.id == document_id).first()
        version = doc.revision_number if doc else 1

        job = ProcessingJob(
            document_id=document_id,
            stage="QUEUED",
            status=JobStatus.QUEUED.value,
            progress=0,
            message="Document queued for background extraction.",
            retry_count=0,
            max_retries=max_retries,
            version=version,
            idempotency_key=idempotency_key
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        if doc:
            doc.status = DocumentStatus.QUEUED.value
            doc.processing_progress = 0
            doc.processing_message = "Queued for processing."
            db.commit()

        logger.info(f"Created persistent processing job {job.id} for document {document_id}")
        return job

    @classmethod
    def enqueue(cls, document_id: str, job_id: Optional[str] = None) -> str:
        """Submit the job to the asynchronous thread pool."""
        def _task_runner():
            db = SessionLocal()
            try:
                cls._execute_job(db, document_id, job_id)
            finally:
                db.close()

        _executor.submit(_task_runner)
        return job_id or ""

    @classmethod
    def _execute_job(cls, db: Session, document_id: str, job_id: Optional[str]):
        """Execute the complete multi-stage pipeline with durable status updates."""
        job = None
        if job_id:
            job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        if not job:
            job = db.query(ProcessingJob).filter(
                ProcessingJob.document_id == document_id
            ).order_by(ProcessingJob.created_at.desc()).first()

        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            logger.error(f"Cannot execute job: Document {document_id} not found.")
            return

        now = datetime.now(timezone.utc)
        if job:
            job.status = JobStatus.PROCESSING.value
            job.stage = "CLASSIFYING"
            job.progress = 10
            job.message = "Classifying document structure and format..."
            job.started_at = now
            db.commit()

        doc.status = DocumentStatus.CLASSIFYING.value
        doc.processing_progress = 10
        doc.processing_started_at = now
        db.commit()

        try:
            # Execute Phase 2 extraction pipeline
            processed_doc = DocumentProcessor.process_document(db, document_id)

            # Check if any high/critical validation issues were raised
            has_warnings = (processed_doc.warning_count or 0) > 0
            final_job_status = JobStatus.REVIEW_REQUIRED.value if has_warnings else JobStatus.COMPLETED.value
            final_doc_status = (
                DocumentStatus.COMPLETED_WITH_WARNINGS.value if has_warnings
                else DocumentStatus.READY.value
            )

            completed_now = datetime.now(timezone.utc)
            if job:
                job.status = final_job_status
                job.stage = "READY"
                job.progress = 100
                job.message = (
                    f"Processing complete: {processed_doc.fact_count} facts extracted. "
                    + (f"{processed_doc.warning_count} quality issues require review." if has_warnings else "All checks clean.")
                )
                job.completed_at = completed_now
                db.commit()

            processed_doc.status = final_doc_status
            processed_doc.processing_progress = 100
            processed_doc.processing_completed_at = completed_now
            db.commit()

            log_audit_event(
                db=db,
                action=AuditAction.DOCUMENT_PROCESSED,
                entity_type="DOCUMENT",
                entity_id=document_id,
                user="MineIntel Pipeline",
                details=f"Pipeline finished: {processed_doc.fact_count} facts, status={final_doc_status}."
            )
            logger.info(f"Job completed successfully for doc {document_id}: status={final_doc_status}")

        except Exception as e:
            logger.error(f"Error processing document {document_id}: {e}\n{traceback.format_exc()}")
            safe_error_msg = f"Extraction failed: {type(e).__name__}: {str(e)[:200]}"

            if job:
                job.retry_count += 1
                if job.retry_count <= job.max_retries:
                    job.status = JobStatus.QUEUED.value
                    job.stage = "RETRY_QUEUED"
                    job.message = f"Attempt {job.retry_count} failed. Re-queued for retry."
                    job.error_details = safe_error_msg
                    db.commit()
                    logger.info(f"Re-enqueuing job {job.id} (attempt {job.retry_count}/{job.max_retries})")
                    cls.enqueue(document_id, job.id)
                    return
                else:
                    job.status = JobStatus.FAILED.value
                    job.stage = "FAILED"
                    job.message = "Processing failed after max retries."
                    job.error_details = safe_error_msg
                    job.completed_at = datetime.now(timezone.utc)
                    db.commit()

            doc.status = DocumentStatus.FAILED.value
            doc.processing_error = safe_error_msg
            doc.processing_message = "Processing failed. Please inspect error or retry."
            db.commit()

    @classmethod
    def retry_job(cls, db: Session, document_id: str) -> Optional[ProcessingJob]:
        """Operator action to re-trigger a failed job."""
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return None

        job = ProcessingJob(
            document_id=document_id,
            stage="QUEUED",
            status=JobStatus.QUEUED.value,
            progress=0,
            message="Operator requested retry.",
            retry_count=0,
            max_retries=3,
            version=doc.revision_number
        )
        db.add(job)
        doc.status = DocumentStatus.QUEUED.value
        doc.processing_error = None
        doc.processing_progress = 0
        db.commit()
        db.refresh(job)

        cls.enqueue(document_id, job.id)
        return job

    @classmethod
    def recover_stuck_jobs(cls, db: Session):
        """Recover jobs left in PROCESSING state across server restarts."""
        stuck_jobs = db.query(ProcessingJob).filter(
            ProcessingJob.status == JobStatus.PROCESSING.value
        ).all()
        for j in stuck_jobs:
            logger.info(f"Recovering stuck job {j.id} for document {j.document_id}")
            j.status = JobStatus.QUEUED.value
            j.stage = "RECOVERED"
            j.message = "Server restarted; job recovered and queued for execution."
            db.commit()
            cls.enqueue(j.document_id, j.id)
