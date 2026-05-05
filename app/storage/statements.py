from io import BytesIO
from uuid import UUID

from fastapi import HTTPException, UploadFile, status

from app.config import get_settings


class MinioStatementStorageService:
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

    def generate_object_name(self, user_id: UUID, statement_id: UUID) -> str:
        return f"{user_id}/{statement_id}.pdf"

    def upload_pdf(
        self,
        user_id: UUID,
        statement_id: UUID,
        file: UploadFile,
        content: bytes,
    ) -> str:
        validate_pdf_upload(file)
        self.ensure_bucket_exists()
        object_name = self.generate_object_name(
            user_id=user_id,
            statement_id=statement_id,
        )
        content_type = file.content_type or "application/pdf"
        self.client.put_object(
            bucket_name=self.bucket_name,
            object_name=object_name,
            data=BytesIO(content),
            length=len(content),
            content_type=content_type,
        )

        return f"{self.bucket_name}/{object_name}"


def validate_pdf_upload(file: UploadFile) -> None:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF statement uploads are supported.",
        )


def upload_statement_pdf(
    user_id: UUID,
    statement_id: UUID,
    file: UploadFile,
    content: bytes,
) -> str:
    return MinioStatementStorageService().upload_pdf(
        user_id=user_id,
        statement_id=statement_id,
        file=file,
        content=content,
    )
