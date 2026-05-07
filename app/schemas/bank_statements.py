from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UploadedStatementMetadata(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "bank_name": "Capitec",
                "object_key": (
                    "input/550e8400-e29b-41d4-a716-446655440000/statement.pdf"
                ),
                "created_at": "2026-05-05T10:00:00Z",
                "updated_at": "2026-05-05T10:00:00Z",
            }
        },
    )

    id: UUID
    bank_name: str
    object_key: str
    created_at: datetime
    updated_at: datetime


class UploadBankStatementResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "uploaded_statement": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "bank_name": "Capitec",
                    "object_key": (
                        "input/550e8400-e29b-41d4-a716-446655440000/" "statement.pdf"
                    ),
                    "created_at": "2026-05-05T10:00:00Z",
                    "updated_at": "2026-05-05T10:00:00Z",
                },
                "download_url": (
                    "http://localhost:8000/api/v1/bank-statement/"
                    "550e8400-e29b-41d4-a716-446655440000/download"
                ),
                "message": (
                    "Bank statement uploaded successfully and processed with "
                    "simulated OCR."
                ),
            }
        },
    )

    uploaded_statement: UploadedStatementMetadata
    download_url: str = ""
    message: str
