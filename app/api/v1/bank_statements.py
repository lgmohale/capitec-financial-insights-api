from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.schemas.bank_statements import UploadStatementResponse
from app.services.bank_statement_service import upload_and_process_bank_statement

router = APIRouter(prefix="/api/v1/bank-statements", tags=["bank statements"])


@router.post(
    "/upload",
    response_model=UploadStatementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a PDF bank statement",
    description=(
        "Uploads a local PDF bank statement to MinIO, simulates OCR processing, "
        "creates statement metadata in PostgreSQL, and generates a random "
        "transaction JSON file as if transactions were extracted from the PDF. "
        "The API response returns statement metadata only and does not expose "
        "internal local transaction file paths."
    ),
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "description": "Invalid upload.",
            "content": {
                "application/json": {
                    "example": {"detail": "Only PDF statement uploads are supported."}
                }
            },
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "Upload or processing failed.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Bank statement upload could not be processed."
                    }
                }
            },
        },
    },
)
async def upload_bank_statement(
    db: Annotated[Session, Depends(get_db)],
    user_names: Annotated[
        str,
        Form(
            description="User names for the uploaded statement.",
            examples=["Lucas George"],
        ),
    ],
    bank_name: Annotated[
        str,
        Form(
            description="Bank statement name or bank name.",
            examples=["FNB Statement April 2026"],
        ),
    ],
    file: Annotated[
        UploadFile,
        File(description="PDF bank statement to store in MinIO."),
    ],
) -> UploadStatementResponse:
    return await upload_and_process_bank_statement(
        user_names=user_names,
        bank_name=bank_name,
        file=file,
        db=db,
    )
