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
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.schemas.bank_statements import UploadBankStatementResponse
from app.services.bank_statement_service import (
    get_uploaded_statement,
    upload_bank_statement_record,
)
from app.storage.object_storage import read_bytes_object

router = APIRouter(prefix="/api/v1/bank-statement", tags=["bank statements"])


@router.post(
    "/uplaod",
    response_model=UploadBankStatementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a PDF statement to MinIO and simulate OCR processing",
    description=("Uploads a PDF bank statement"),
)
async def upload_bank_statement(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    bank_name: Annotated[
        str,
        Form(description="Bank or statement name.", examples=["Capitec"]),
    ],
    file: Annotated[
        UploadFile,
        File(description="PDF bank statement to upload."),
    ],
) -> UploadBankStatementResponse:
    response = upload_bank_statement_record(
        bank_name=bank_name,
        filename=file.filename or "",
        content_type=file.content_type or "",
        content=await file.read(),
        db=db,
    )
    response.download_url = str(
        request.url_for(
            "download_bank_statement",
            statement_id=str(response.uploaded_statement.id),
        )
    )
    return response


@router.get(
    "/{statement_id}/download",
    name="download_bank_statement",
    summary="Download bank statement",
    description=("Streams the uploaded PDF bank statement from MinIO through the API."),
    responses={
        status.HTTP_200_OK: {
            "description": "Uploaded PDF bank statement.",
            "content": {"application/pdf": {}},
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "Uploaded statement not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "Uploaded statement not found."}
                }
            },
        },
    },
)
def download_bank_statement(
    statement_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    uploaded_statement = get_uploaded_statement(statement_id=statement_id, db=db)
    if uploaded_statement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Uploaded statement not found.",
        )

    return Response(
        content=read_bytes_object(uploaded_statement.object_key),
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="bank-statement-{statement_id}.pdf"'
            )
        },
    )
