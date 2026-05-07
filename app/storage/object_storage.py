import json
from io import BytesIO
from typing import Any

from app.config import get_settings
from app.core.logging import get_logger
from app.core.metrics import MINIO_UPLOAD_FAILURES, MINIO_UPLOADS

logger = get_logger(__name__)


class MinioObjectStorageService:
    def __init__(self) -> None:
        from minio import Minio

        settings = get_settings()
        self.bucket_name = settings.minio_bucket
        self.client = Minio(
            settings.minio_server,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_use_ssl,
        )

    def ensure_bucket_exists(self) -> None:
        if not self.client.bucket_exists(self.bucket_name):
            self.client.make_bucket(self.bucket_name)

    def upload_bytes(
        self,
        object_key: str,
        content: bytes,
        content_type: str,
    ) -> str:
        try:
            logger.info(
                "MinIO upload started",
                extra={"event_name": "minio_upload_started"},
            )
            self.ensure_bucket_exists()
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_key,
                data=BytesIO(content),
                length=len(content),
                content_type=content_type,
            )
            MINIO_UPLOADS.labels("upload_completed").inc()
            logger.info(
                "MinIO upload completed",
                extra={"event_name": "minio_upload_completed"},
            )
            return object_key
        except Exception:
            MINIO_UPLOAD_FAILURES.labels("upload_failed").inc()
            logger.exception(
                "MinIO upload failed",
                extra={"event_name": "minio_upload_failed"},
            )
            raise

    def upload_json(self, object_key: str, value: Any) -> str:
        return self.upload_bytes(
            object_key=object_key,
            content=json.dumps(value, indent=2).encode("utf-8"),
            content_type="application/json",
        )

    def read_json(self, object_key: str) -> Any:
        object_key = self.normalise_object_key(object_key)
        response = self.client.get_object(self.bucket_name, object_key)
        try:
            return json.loads(response.read().decode("utf-8"))
        finally:
            response.close()
            response.release_conn()

    def read_bytes(self, object_key: str) -> bytes:
        object_key = self.normalise_object_key(object_key)
        response = self.client.get_object(self.bucket_name, object_key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def object_exists(self, object_key: str) -> bool:
        object_key = self.normalise_object_key(object_key)
        try:
            self.client.stat_object(self.bucket_name, object_key)
        except Exception:
            return False
        return True

    def delete_object(self, object_key: str) -> None:
        object_key = self.normalise_object_key(object_key)
        self.client.remove_object(self.bucket_name, object_key)

    def object_reference(self, object_key: str) -> str:
        return f"{self.bucket_name}/{object_key}"

    def normalise_object_key(self, object_key: str) -> str:
        bucket_prefix = f"{self.bucket_name}/"
        if object_key.startswith(bucket_prefix):
            return object_key.removeprefix(bucket_prefix)
        return object_key


def upload_bytes_object(object_key: str, content: bytes, content_type: str) -> str:
    return MinioObjectStorageService().upload_bytes(
        object_key=object_key,
        content=content,
        content_type=content_type,
    )


def upload_json_object(object_key: str, value: Any) -> str:
    return MinioObjectStorageService().upload_json(object_key=object_key, value=value)


def read_json_object(object_key: str) -> Any:
    return MinioObjectStorageService().read_json(object_key)


def read_bytes_object(object_key: str) -> bytes:
    return MinioObjectStorageService().read_bytes(object_key)


def object_exists(object_key: str) -> bool:
    return MinioObjectStorageService().object_exists(object_key)


def delete_object(object_key: str) -> None:
    MinioObjectStorageService().delete_object(object_key)
