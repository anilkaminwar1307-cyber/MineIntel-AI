"""
Upload and Ingestion Security Validator
────────────────────────────────────────
Deep file validation according to SIH 2026 PS 26023 standards:
- File signature & MIME type validation
- Deep OOXML package inspection (ZIP magic alone is rejected; verifies internal XML structures)
- Zip bomb & polyglot file detection
- PDF encryption & page count verification
- Image structure verification (PNG, JPG, TIFF)
- Path traversal prevention & filename sanitization
"""
import io
import os
import re
import zipfile
import hashlib
from typing import Tuple, Dict, Any, Optional
from fastapi import HTTPException, status
from PIL import Image

from app.core.config import settings
from app.core.logging import logger
from app.models.enums import FileType

ALLOWED_EXTENSIONS = {
    ".pdf": FileType.PDF,
    ".docx": FileType.DOCX,
    ".xlsx": FileType.XLSX,
    ".xls": FileType.XLS,
    ".csv": FileType.CSV,
    ".txt": FileType.TXT,
    ".png": FileType.PNG,
    ".jpg": FileType.JPG,
    ".jpeg": FileType.JPEG,
    ".tiff": FileType.TIFF,
    ".tif": FileType.TIFF,
}

MAX_PAGE_COUNT = 500
MAX_UNCOMPRESSED_ARCHIVE_BYTES = 100 * 1024 * 1024  # 100 MB
MAX_COMPRESSION_RATIO = 100.0


def sanitize_filename(filename: str) -> str:
    """Strip path traversal, replace unsafe characters, and normalize name."""
    clean_name = os.path.basename(filename)
    clean_name = re.sub(r'[^a-zA-Z0-9._-]', '_', clean_name)
    if clean_name.startswith('.'):
        clean_name = 'doc_' + clean_name.lstrip('.')
    return clean_name or "uploaded_document"


def validate_file_signature(content: bytes, ext: str) -> None:
    """Verify magic bytes and reject polyglots / executable payloads."""
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file rejected: 0 bytes uploaded."
        )

    # Disallow Windows PE (.exe, .dll) and Linux ELF binaries masquerading as documents
    if content.startswith(b"MZ") or content.startswith(b"\x7fELF"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Security Violation: Binary executable detected masquerading as document."
        )

    if ext == ".pdf":
        if not content.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Security Violation: Invalid PDF signature (missing %PDF- header)."
            )
    elif ext in (".docx", ".xlsx"):
        if not content.startswith(b"PK\x03\x04"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Security Violation: Invalid OOXML container signature for '{ext}'."
            )
    elif ext == ".xls":
        # Legacy OLE2 Compound File Header
        if not (content.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1") or content.startswith(b"PK\x03\x04")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Security Violation: Invalid legacy Excel binary signature."
            )
    elif ext == ".png":
        if not content.startswith(b"\x89PNG\r\n\x1a\n"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Security Violation: Invalid PNG image signature."
            )
    elif ext in (".jpg", ".jpeg"):
        if not content.startswith(b"\xff\xd8\xff"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Security Violation: Invalid JPEG image signature."
            )
    elif ext in (".tiff", ".tif"):
        # Intel (II) or Motorola (MM) TIFF signature
        if not (content.startswith(b"II*\x00") or content.startswith(b"MM\x00*")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Security Violation: Invalid TIFF image signature."
            )


def validate_ooxml_package(content: bytes, ext: str) -> None:
    """Deep inspect OOXML (.docx/.xlsx) zip structure to prevent polyglots and zip bombs."""
    try:
        with zipfile.ZipFile(io.BytesIO(content), "r") as zf:
            total_uncompressed = 0
            file_names = set(zf.namelist())

            # 1. Require [Content_Types].xml in root
            if "[Content_Types].xml" not in file_names:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid OOXML file: missing '[Content_Types].xml' in {ext} package."
                )

            # 2. Format-specific internal parts
            if ext == ".docx":
                if not any(f.startswith("word/") for f in file_names):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid DOCX package: missing 'word/' document payload."
                    )
            elif ext == ".xlsx":
                if not any(f.startswith("xl/") for f in file_names):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid XLSX package: missing 'xl/' workbook payload."
                    )

            # 3. Zip bomb & polyglot check
            for zinfo in zf.infolist():
                total_uncompressed += zinfo.file_size
                if total_uncompressed > MAX_UNCOMPRESSED_ARCHIVE_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Security alert: Archive exceeds maximum uncompressed size of {MAX_UNCOMPRESSED_ARCHIVE_BYTES // (1024*1024)}MB (potential zip bomb)."
                    )

            if len(content) > 0:
                ratio = total_uncompressed / len(content)
                if ratio > MAX_COMPRESSION_RATIO:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Security alert: Excessive compression ratio ({ratio:.1f}x) detected."
                    )

    except zipfile.BadZipFile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Corrupted or invalid OOXML ZIP container for '{ext}'."
        )


def validate_pdf_structure(content: bytes, clean_name: str) -> int:
    """Inspect PDF structure, ensure not encrypted, and return page count."""
    try:
        import fitz
        pdf_doc = fitz.open(stream=content, filetype="pdf")
        if pdf_doc.is_encrypted:
            pdf_doc.close()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Password-protected or encrypted PDFs cannot be processed. Please decrypt '{clean_name}' before uploading."
            )
        page_count = len(pdf_doc)
        pdf_doc.close()

        if page_count > MAX_PAGE_COUNT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"PDF exceeds maximum allowed page count of {MAX_PAGE_COUNT} (contains {page_count} pages)."
            )
        return page_count
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"PDF pre-inspection parsing warning for {clean_name}: {e}")
        return 0


def validate_image_structure(content: bytes, ext: str) -> Tuple[int, int]:
    """Verify image bytes using PIL."""
    try:
        with Image.open(io.BytesIO(content)) as img:
            img.verify()
            width, height = img.size
            return width, height
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid or corrupted image data for '{ext}': {e}"
        )


def validate_uploaded_file(
    filename: str,
    content: bytes,
    content_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Complete security and structural validation of uploaded file.
    Returns metadata dictionary on success or raises HTTPException.
    """
    clean_name = sanitize_filename(filename)
    ext = os.path.splitext(clean_name)[1].lower()
    file_size = len(content)

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Empty file rejected. '{clean_name}' contains 0 bytes."
        )

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file_size > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB."
        )

    if ext not in ALLOWED_EXTENSIONS:
        allowed_list = ", ".join(sorted(ALLOWED_EXTENSIONS.keys()))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Supported formats: {allowed_list}"
        )

    file_type = ALLOWED_EXTENSIONS[ext]

    # 1. Validate signature / magic bytes
    validate_file_signature(content, ext)

    # 2. Deep OOXML inspection
    if ext in (".docx", ".xlsx"):
        validate_ooxml_package(content, ext)

    # 3. PDF inspection
    page_count = 0
    if ext == ".pdf":
        page_count = validate_pdf_structure(content, clean_name)

    # 4. Image inspection
    image_dims = None
    if ext in (".png", ".jpg", ".jpeg", ".tiff", ".tif"):
        image_dims = validate_image_structure(content, ext)

    # 5. Compute SHA-256 fingerprint
    sha256_hash = hashlib.sha256(content).hexdigest()

    return {
        "clean_filename": clean_name,
        "extension": ext,
        "file_type": file_type,
        "file_size": file_size,
        "sha256": sha256_hash,
        "page_count": page_count,
        "image_dims": image_dims,
    }
