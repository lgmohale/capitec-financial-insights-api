from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.db.models import LinkedAccount, User
from app.schemas.bank_accounts import LinkBankAccountResponse
from app.storage.transactions import write_starter_transactions


def create_linked_account(
    name: str,
    bank_name: str,
    db: Session,
    user_id: Optional[UUID] = None,  # noqa: UP007
    linked_account_id: Optional[UUID] = None,  # noqa: UP007
) -> tuple[LinkBankAccountResponse, Path]:
    user = User(id=user_id or uuid4(), name=name)
    linked_account_id = linked_account_id or uuid4()
    linked_account = LinkedAccount(
        user_id=user.id,
        id=linked_account_id,
        bank_name=bank_name,
    )

    file_path = write_starter_transactions(linked_account_id)
    try:
        db.add(user)
        db.flush()
        db.add(linked_account)
        db.commit()
    except Exception:
        db.rollback()
        file_path.unlink(missing_ok=True)
        raise

    db.refresh(user)
    db.refresh(linked_account)

    return LinkBankAccountResponse(user=user, linked_account=linked_account), file_path
