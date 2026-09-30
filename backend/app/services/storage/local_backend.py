"""
Local Disk Storage Backend Implementation
─────────────────────────────────────────
Implements atomic writes (tempfile + atomic os.replace) and path traversal prevention.
Generates portable relative object keys.
"""
import os
import uuid
import tempfile
from pathlib import Path
from typing import Optional
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.logging import logger
from app.services.storage.base import StorageBackend


class LocalStorageBackend(StorageBackend):
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir or settings.UPLOAD_DIR).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _safe_path(self, object_key: str) -> Path:
        """Resolve path ensuring no path traversal outside base_dir."""
        # Normalize relative key (strip leading slashes/uploads prefix if passed)
        clean_key = object_key.replace("\\", "/").lstrip("/")
        if clean_key.startswith("uploads/"):
            clean_key = clean_key[len("uploads/"):]

        target = (self.base_dir / clean_key).resolve()
        if not str(target).startswith(str(self.base_dir)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Security Violation: Path traversal outside upload storage boundary."
            )
        return target

    def save_bytes(self, content: bytes, object_key: str) -> str:
        """
        Atomically write content to disk using tempfile in same directory
        followed by atomic rename (os.replace).
        """
        target_path = self._safe_path(object_key)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write to temporary file in same folder
        temp_file = target_path.parent / f".tmp_{uuid.uuid4().hex}"
        try:
            with open(temp_file, "wb") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())

            # Atomic commit
            os.replace(temp_file, target_path)
            logger.info(f"Atomically stored {len(content)} bytes to '{target_path.name}'.")
        except Exception as e:
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to persist document to storage: {e}"
            )

        # Return standardized relative object key
        rel_key = f"uploads/{target_path.name}"
        return rel_key

    def get_bytes(self, object_key: str) -> bytes:
        target_path = self._safe_path(object_key)
        if not target_path.exists() or not target_path.is_file():
            raise FileNotFoundError(f"Storage object '{object_key}' does not exist on disk.")
        with open(target_path, "rb") as f:
            return f.read()

    def delete(self, object_key: str) -> bool:
        try:
            target_path = self._safe_path(object_key)
            if target_path.exists() and target_path.is_file():
                target_path.unlink()
                logger.info(f"Deleted storage object: {object_key}")
                return True
        except Exception as e:
            logger.error(f"Error deleting storage object '{object_key}': {e}")
        return False

    def exists(self, object_key: str) -> bool:
        try:
            target_path = self._safe_path(object_key)
            return target_path.exists() and target_path.is_file()
        except Exception:
            return False

    def resolve_path(self, object_key: str) -> Optional[Path]:
        try:
            target_path = self._safe_path(object_key)
            if target_path.exists() and target_path.is_file():
                return target_path
            return None
        except Exception:
            return None


local_storage_backend = LocalStorageBackend()
