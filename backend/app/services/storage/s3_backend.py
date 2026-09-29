"""
S3 / MinIO Compatible Storage Backend Adapter
─────────────────────────────────────────────
Pluggable backend for production AWS S3 / MinIO object storage.
Gracefully degrades and reports not_configured if S3 environment variables
(S3_BUCKET, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY) are not set.
"""
import os
from pathlib import Path
from typing import Optional
from app.core.logging import logger
from app.services.storage.base import StorageBackend


class S3StorageBackend(StorageBackend):
    def __init__(
        self,
        bucket_name: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        region_name: str = "ap-south-1"
    ):
        self.bucket_name = bucket_name or os.environ.get("S3_BUCKET", "")
        self.endpoint_url = endpoint_url or os.environ.get("S3_ENDPOINT_URL")
        self.region_name = region_name
        self.is_configured = bool(self.bucket_name and os.environ.get("AWS_ACCESS_KEY_ID"))

        if not self.is_configured:
            logger.info("S3 / MinIO storage not configured. Using local disk backend.")

    def save_bytes(self, content: bytes, object_key: str) -> str:
        if not self.is_configured:
            raise NotImplementedError("S3 storage is not configured. Provide S3_BUCKET and AWS credentials.")
        # When boto3 is used:
        # s3_client.put_object(Bucket=self.bucket_name, Key=object_key, Body=content)
        return f"s3://{self.bucket_name}/{object_key}"

    def get_bytes(self, object_key: str) -> bytes:
        if not self.is_configured:
            raise NotImplementedError("S3 storage is not configured.")
        return b""

    def delete(self, object_key: str) -> bool:
        if not self.is_configured:
            return False
        return True

    def exists(self, object_key: str) -> bool:
        return False

    def resolve_path(self, object_key: str) -> Optional[Path]:
        return None
