"""
Storage Backend Abstraction Interface
─────────────────────────────────────
Supports both local file storage and S3/MinIO compatible object stores.
Ensures stable relative object keys in the database and atomic file writes.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, BinaryIO


class StorageBackend(ABC):
    @abstractmethod
    def save_bytes(self, content: bytes, object_key: str) -> str:
        """Atomically persist content and return the stable relative object key."""
        pass

    @abstractmethod
    def get_bytes(self, object_key: str) -> bytes:
        """Retrieve file bytes for the given object key."""
        pass

    @abstractmethod
    def delete(self, object_key: str) -> bool:
        """Delete file associated with the object key."""
        pass

    @abstractmethod
    def exists(self, object_key: str) -> bool:
        """Check if the object exists in storage."""
        pass

    @abstractmethod
    def resolve_path(self, object_key: str) -> Optional[Path]:
        """Resolve to a local Path if stored locally, or None if remote."""
        pass
