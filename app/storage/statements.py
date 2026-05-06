from uuid import UUID

from fastapi import HTTPException, UploadFile, status

from app.storage.object_storage import upload_bytes_object


class MinioStatementStorageService:
    def generate_object_name(self, user_id: UUID, statement_id: UUID) -> str:
        return f"input/{user_id}/{statement_id}.pdf"

    def upload_pdf(
        self,
        user_id: UUID,
        statement_id: UUID,
        file: UploadFile,
        content: bytes,
    ) -> str:
        validate_pdf_upload(file)
        object_name = self.generate_object_name(
            user_id=user_id,
            statement_id=statement_id,
        )
        return upload_bytes_object(
            object_key=object_name,
            content=content,
            content_type=file.content_type or "application/pdf",
        )


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
