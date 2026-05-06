from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.api.v1.download_links import bank_statement_pdf_download_url
from app.db.models import BankStatement
from app.schemas.bank_statements import UploadStatementResponse
from app.services.bank_statement_service import upload_and_process_bank_statement
from app.storage.object_storage import read_bytes_object

router = APIRouter(prefix="/api/v1/bank-statements", tags=["bank statements"])


@router.post(
    "/upload",
    response_model=UploadStatementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a PDF bank statement",
    description=(
        "Uploads a local PDF bank statement to MinIO, simulates OCR processing, "
        "creates statement metadata in PostgreSQL, and generates a random "
        "transaction JSON object in MinIO as if transactions were extracted "
        "from the PDF. The API response returns statement metadata and MinIO "
        "object keys only."
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
    request: Request,
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
    response = await upload_and_process_bank_statement(
        user_names=user_names,
        bank_name=bank_name,
        file=file,
        db=db,
    )
    response.bank_statement_pdf_download_url = bank_statement_pdf_download_url(
        request,
        response.id,
    )
    return response


@router.get(
    "/{statement_id}/download",
    name="download_bank_statement_pdf",
    summary="Download uploaded bank statement PDF",
    description=(
        "Streams the uploaded bank statement PDF from MinIO through the API so "
        "reviewers can download it from Swagger without using internal MinIO "
        "container URLs."
    ),
    responses={
        status.HTTP_200_OK: {
            "description": "Uploaded PDF bank statement.",
            "content": {"application/pdf": {}},
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "Bank statement not found.",
            "content": {
                "application/json": {"example": {"detail": "Bank statement not found."}}
            },
        },
    },
)
def download_bank_statement_pdf(
    statement_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    bank_statement = db.scalar(
        select(BankStatement).where(BankStatement.id == statement_id)
    )
    if bank_statement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bank statement not found.",
        )

    return Response(
        content=read_bytes_object(bank_statement.file_url),
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="bank-statement-{statement_id}.pdf"'
            )
        },
    )
