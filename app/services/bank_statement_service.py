from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.db.models import BankStatement, User
from app.schemas.bank_statements import UploadStatementResponse
from app.storage.statements import upload_statement_pdf
from app.storage.transactions import write_starter_transactions

SUCCESS_MESSAGE = "Bank statement uploaded successfully and queued for processing."


async def upload_and_process_bank_statement(
    user_names: str,
    bank_name: str,
    file: UploadFile,
    db: Session,
) -> UploadStatementResponse:
    user_id = uuid4()
    statement_id = uuid4()
    user = User(id=user_id, name=user_names)
    file_url = upload_statement_pdf(
        user_id=user_id,
        statement_id=statement_id,
        file=file,
        content=await file.read(),
    )

    transaction_file_path = write_starter_transactions(statement_id)
    bank_statement = BankStatement(
        id=statement_id,
        user_id=user_id,
        bank_name=bank_name,
        file_url=file_url,
    )
    try:
        db.add(user)
        db.flush()
        db.add(bank_statement)
        db.commit()
    except Exception:
        db.rollback()
        transaction_file_path.unlink(missing_ok=True)
        raise

    db.refresh(bank_statement)

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
