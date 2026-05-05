from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.db.models import BankStatement
from app.schemas.bank_accounts import UploadStatementResponse
from app.services.bank_account_service import create_linked_account
from app.storage.statements import upload_statement_pdf

SUCCESS_MESSAGE = "Bank statement uploaded successfully and queued for processing."


async def upload_and_process_bank_statement(
    user_names: str,
    bank_name: str,
    file: UploadFile,
    db: Session,
) -> UploadStatementResponse:
    user_id = uuid4()
    statement_id = uuid4()
    file_url = upload_statement_pdf(
        user_id=user_id,
        statement_id=statement_id,
        file=file,
        content=await file.read(),
    )

    linked_account_response, _ = create_linked_account(
        name=user_names,
        bank_name=bank_name,
        db=db,
        user_id=user_id,
        linked_account_id=statement_id,
    )
    bank_statement = save_bank_statement_record(
        statement_id=linked_account_response.linked_account.id,
        user_id=linked_account_response.user.id,
        bank_name=bank_name,
        file_url=file_url,
        db=db,
    )

    return UploadStatementResponse(
        id=bank_statement.id,
        user_id=bank_statement.user_id,
        bank_name=bank_statement.bank_name,
        file_url=bank_statement.file_url,
        message=SUCCESS_MESSAGE,
    )


def save_bank_statement_record(
    statement_id: UUID,
    user_id: UUID,
    bank_name: str,
    file_url: str,
    db: Session,
) -> BankStatement:
    bank_statement = BankStatement(
        id=statement_id,
        user_id=user_id,
        bank_name=bank_name,
        file_url=file_url,
    )
    try:
        db.add(bank_statement)
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(bank_statement)
    return bank_statement
