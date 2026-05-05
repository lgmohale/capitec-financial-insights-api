from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.schemas.bank_accounts import (
    LinkBankAccountRequest,
    LinkBankAccountResponse,
    UploadStatementResponse,
)
from app.services.bank_account_service import create_linked_account
from app.services.bank_statement_service import upload_and_process_bank_statement

router = APIRouter(prefix="/api/v1/bank-accounts", tags=["bank accounts"])


@router.post(
    "/link",
    response_model=LinkBankAccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Link a simulated bank account",
    description=(
        "Creates a user metadata row, generates a linked account ID, writes "
        "a random transaction history to `data/input/{linked_account_id}.json`, "
        "and stores only linked account metadata in PostgreSQL. Generated histories "
        "cover more than 3 months and include salary, deposits, withdrawals, and "
        "at least 7 transactions per week."
    ),
)
def link_bank_account(
    request: LinkBankAccountRequest,
    db: Annotated[Session, Depends(get_db)],
) -> LinkBankAccountResponse:
    response, _ = create_linked_account(
        name=request.name,
        bank_name=request.bank_name,
        db=db,
    )
    return response


@router.post(
    "/statement-upload",
    response_model=UploadStatementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a PDF bank statement",
    description=(
        "Uploads a local PDF bank statement to MinIO, simulates OCR processing, "
        "then creates the same user, linked account metadata, and random "
        "transaction JSON file used by the simulated linking flow. PostgreSQL "
        "stores only metadata. The API response returns statement metadata only "
        "and does not expose internal local transaction file paths."
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
            description="User names for the linked account.",
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
