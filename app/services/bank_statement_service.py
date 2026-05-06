from contextlib import suppress
from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.db.models import BankStatement, User
from app.schemas.bank_statements import UploadStatementResponse
from app.storage.object_storage import delete_object
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
    created_object_keys = []
    try:
        file_url = upload_statement_pdf(
            user_id=user_id,
            statement_id=statement_id,
            file=file,
            content=await file.read(),
        )
        created_object_keys.append(file_url)

        transaction_object_key = write_starter_transactions(statement_id)
        created_object_keys.append(transaction_object_key)

        bank_statement = BankStatement(
            id=statement_id,
            user_id=user_id,
            bank_name=bank_name,
            file_url=file_url,
        )
        db.add(user)
        db.flush()
        db.add(bank_statement)
        db.commit()
    except Exception:
        db.rollback()
        for object_key in created_object_keys:
            with suppress(Exception):
                delete_object(object_key)
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
