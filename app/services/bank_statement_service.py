from contextlib import suppress
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.models import UploadedStatement
from app.schemas.bank_statements import (
    UploadBankStatementResponse,
    UploadedStatementMetadata,
)
from app.storage.object_storage import delete_object, upload_bytes_object
from app.storage.transactions import write_starter_transactions

SUCCESS_MESSAGE = (
    "Bank statement uploaded successfully and processed with simulated OCR."
)
logger = get_logger(__name__)


def upload_bank_statement_record(
    bank_name: str,
    filename: str,
    content_type: str,
    content: bytes,
    db: Session,
) -> UploadBankStatementResponse:
    validate_pdf_upload(filename=filename, content_type=content_type, content=content)
    statement_id = uuid4()
    pdf_object_key = pdf_statement_object_key(statement_id)
    created_object_keys = []
    try:
        logger.info(
            "Bank statement upload started",
            extra={
                "statement_id": str(statement_id),
                "event_name": "bank_statement_upload_started",
            },
        )
        upload_bytes_object(
            object_key=pdf_object_key,
            content=content,
            content_type="application/pdf",
        )
        created_object_keys.append(pdf_object_key)
        logger.info(
            "Simulated OCR processing started",
            extra={
                "statement_id": str(statement_id),
                "event_name": "simulated_ocr_processing_started",
            },
        )
        transaction_object_key = write_starter_transactions(statement_id)
        created_object_keys.append(transaction_object_key)
        uploaded_statement = UploadedStatement(
            id=statement_id,
            bank_name=bank_name,
            object_key=pdf_object_key,
        )
        db.add(uploaded_statement)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception(
            "Bank statement upload failed",
            extra={
                "statement_id": str(statement_id),
                "event_name": "bank_statement_upload_failed",
            },
        )
        for object_key in created_object_keys:
            with suppress(Exception):
                delete_object(object_key)
        raise

    db.refresh(uploaded_statement)
    logger.info(
        "Bank statement uploaded and processed",
        extra={
            "statement_id": str(statement_id),
            "event_name": "bank_statement_upload_completed",
        },
    )

    return UploadBankStatementResponse(
        uploaded_statement=UploadedStatementMetadata.model_validate(uploaded_statement),
        message=SUCCESS_MESSAGE,
    )


def get_uploaded_statement(statement_id: UUID, db: Session) -> UploadedStatement | None:
    return db.scalar(
        select(UploadedStatement).where(UploadedStatement.id == statement_id)
    )


def pdf_statement_object_key(statement_id: UUID) -> str:
    return f"input/{statement_id}/statement.pdf"


def validate_pdf_upload(filename: str, content_type: str, content: bytes) -> None:
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF bank statement uploads are supported.",
        )
    if content_type and content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF bank statement uploads are supported.",
        )
    if not content.startswith(b"%PDF"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded bank statement is not a valid PDF.",
        )
