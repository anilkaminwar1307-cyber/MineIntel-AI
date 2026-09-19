import os
import re
import uuid
import aiofiles
from pathlib import Path
from typing import Tuple
from fastapi import UploadFile, HTTPException
from app.core.config import settings
from app.core.logging import logger
from app.models.enums import FileType

# Mapping extension to canonical FileType and mime checks
EXTENSION_MAP = {
    ".pdf": FileType.PDF,
    ".xlsx": FileType.XLSX,
    ".xls": FileType.XLS,
    ".csv": FileType.CSV,
    ".txt": FileType.TXT,
    ".png": FileType.PNG,
    ".jpg": FileType.JPG,
    ".jpeg": FileType.JPEG,
}

MIME_MAP = {
    FileType.PDF: ["application/pdf"],
    FileType.XLSX: ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"],
    FileType.XLS: ["application/vnd.ms-excel"],
    FileType.CSV: ["text/csv", "text/plain", "application/csv"],
    FileType.TXT: ["text/plain"],
    FileType.PNG: ["image/png"],
    FileType.JPG: ["image/jpeg"],
    FileType.JPEG: ["image/jpeg"],
}


class LocalStorageService:
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir or settings.UPLOAD_DIR).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def sanitize_filename(self, filename: str) -> str:
        """Strip path traversal, replace unsafe characters, and normalize name."""
        # Strip directory components
        clean_name = os.path.basename(filename)
        # Remove any non-alphanumeric chars except dots, underscores, hyphens
        clean_name = re.sub(r'[^a-zA-Z0-9._-]', '_', clean_name)
        # Prevent hidden files
        if clean_name.startswith('.'):
            clean_name = 'doc_' + clean_name.lstrip('.')
        return clean_name or "uploaded_document"

    def validate_file(self, filename: str, content_type: str, file_size: int) -> Tuple[FileType, str]:
        """Validate extension and size, returning (FileType, sanitized_name)."""
        clean_name = self.sanitize_filename(filename)
        ext = os.path.splitext(clean_name)[1].lower()

        if ext not in EXTENSION_MAP:
            allowed = ", ".join(EXTENSION_MAP.keys())
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file extension '{ext}'. Allowed formats: {allowed}"
            )

        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if file_size > max_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB."
            )

        file_type = EXTENSION_MAP[ext]
        return file_type, clean_name

    async def save_file(self, upload_file: UploadFile) -> Tuple[str, str, int, FileType]:
        """
        Saves UploadFile safely into storage.
        Returns: (stored_filename, absolute_storage_path, file_size_bytes, file_type)
        """
        # Read content to measure size and validate
        content = await upload_file.read()
        file_size = len(content)
        
        file_type, clean_name = self.validate_file(
            upload_file.filename or "unknown_file",
            upload_file.content_type or "application/octet-stream",
            file_size
        )

        # Generate unique storage filename to avoid collisions and directory tampering
        file_id = str(uuid.uuid4())
        ext = os.path.splitext(clean_name)[1].lower()
        base = os.path.splitext(clean_name)[0][:40]  # truncate overly long names
        stored_filename = f"{file_id}_{base}{ext}"

        destination_path = (self.base_dir / stored_filename).resolve()

        # Enforce path traversal prevention: ensure destination is within base_dir
        if not str(destination_path).startswith(str(self.base_dir)):
            raise HTTPException(status_code=400, detail="Security violation: Path traversal detected.")

        async with aiofiles.open(destination_path, "wb") as f:
            await f.write(content)

        logger.info(f"Stored file '{clean_name}' as '{stored_filename}' ({file_size} bytes)")
        return stored_filename, str(destination_path), file_size, file_type

    def delete_file(self, stored_filename: str) -> bool:
        """Safely delete file from storage."""
        target_path = (self.base_dir / os.path.basename(stored_filename)).resolve()
        if not str(target_path).startswith(str(self.base_dir)):
            logger.warning(f"Prevented unsafe deletion path: {stored_filename}")
            return False

        if target_path.exists() and target_path.is_file():
            try:
                target_path.unlink()
                logger.info(f"Deleted file: {target_path}")
                return True
            except Exception as e:
                logger.error(f"Error deleting file {target_path}: {e}")
                return False
        return False


storage_service = LocalStorageService()
