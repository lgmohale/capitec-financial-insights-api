from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BankStatementMetadata(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "650e8400-e29b-41d4-a716-446655440000",
                "bank_name": "FNB Statement April 2026",
                "file_url": (
                    "input/650e8400-e29b-41d4-a716-446655440000/"
                    "550e8400-e29b-41d4-a716-446655440000.pdf"
                ),
                "created_at": "2026-05-05T10:00:00Z",
            }
        },
    )

    id: UUID
    user_id: UUID
    bank_name: str
    file_url: str
    created_at: datetime


class UploadStatementResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "650e8400-e29b-41d4-a716-446655440000",
                "bank_name": "FNB Statement April 2026",
                "file_url": (
                    "input/650e8400-e29b-41d4-a716-446655440000/"
                    "550e8400-e29b-41d4-a716-446655440000.pdf"
                ),
                "bank_statement_pdf_download_url": (
                    "http://localhost:8000/api/v1/bank-statements/"
                    "550e8400-e29b-41d4-a716-446655440000/download"
                ),
                "message": (
                    "Bank statement uploaded successfully and queued for processing."
                ),
            }
        },
    )

    id: UUID
    user_id: UUID
    bank_name: str
    file_url: str
    bank_statement_pdf_download_url: str = ""
    message: str
