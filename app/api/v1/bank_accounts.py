from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.db.models import LinkedAccount, User
from app.schemas.bank_accounts import (
    LinkBankAccountRequest,
    LinkBankAccountResponse,
)
from app.storage.transactions import write_starter_transactions

router = APIRouter(prefix="/api/v1/bank-accounts", tags=["bank accounts"])


@router.post(
    "/link",
    response_model=LinkBankAccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Link a simulated bank account",
    description=(
        "Creates a user metadata row, generates a linked account UUID, writes "
        "a random transaction history to `data/input/{linked_account_uuid}.json`, "
        "and stores only linked account metadata in PostgreSQL. Generated histories "
        "cover more than 3 months and include salary, deposits, withdrawals, and "
        "at least 7 transactions per week."
    ),
)
def link_bank_account(
    request: LinkBankAccountRequest,
    db: Annotated[Session, Depends(get_db)],
) -> LinkBankAccountResponse:
    user = User(uuid=uuid4(), name=request.name)
    linked_account_uuid = uuid4()
    linked_account = LinkedAccount(
        user_id=user.uuid,
        uuid=linked_account_uuid,
        bank_name=request.bank_name,
    )

    file_path = write_starter_transactions(linked_account_uuid)
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

    return LinkBankAccountResponse(user=user, linked_account=linked_account)
