import json
from collections import Counter
from datetime import date, datetime, timezone
from uuid import UUID

from app.api.v1.bank_accounts import link_bank_account
from app.schemas.bank_accounts import LinkBankAccountRequest
from app.storage import transactions
from app.storage.transactions import MIN_HISTORY_WEEKS, MIN_TRANSACTIONS_PER_WEEK


class FakeSession:
    def __init__(self) -> None:
        self.added = []
        self.committed = False
        self.rolled_back = False

    def add(self, item: object) -> None:
        self.added.append(item)

    def flush(self) -> None:
        pass

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def refresh(self, item: object) -> None:
        now = datetime(2026, 5, 5, tzinfo=timezone.utc)  # noqa: UP017
        item.created_at = now
        if hasattr(item, "updated_at"):
            item.updated_at = now


def test_link_bank_account_creates_metadata_and_transaction_file(
    tmp_path,
    monkeypatch,
) -> None:
    input_dir = tmp_path / "data" / "input"
    monkeypatch.setattr(transactions, "INPUT_DIR", input_dir)
    db = FakeSession()
    request = LinkBankAccountRequest(name="Lucas George", bank_name="Capitec")

    response = link_bank_account(request=request, db=db)

    assert db.committed is True
    assert db.rolled_back is False
    assert len(db.added) == 2
    assert response.user.name == "Lucas George"
    assert response.linked_account.bank_name == "Capitec"
    assert response.linked_account.user_id == response.user.uuid

    linked_account_uuid = response.linked_account.uuid
    transaction_file = input_dir / f"{linked_account_uuid}.json"

    assert isinstance(linked_account_uuid, UUID)
    assert transaction_file.exists()

    created_transactions = json.loads(transaction_file.read_text(encoding="utf-8"))
    transaction_dates = [
        date.fromisoformat(transaction["date"]) for transaction in created_transactions
    ]
    first_transaction_date = min(transaction_dates)
    weekly_counts = Counter(
        (transaction_date - first_transaction_date).days // 7
        for transaction_date in transaction_dates
        if (transaction_date - first_transaction_date).days // 7 < MIN_HISTORY_WEEKS
    )

    assert len(created_transactions) >= MIN_HISTORY_WEEKS * MIN_TRANSACTIONS_PER_WEEK
    assert (max(transaction_dates) - first_transaction_date).days > 90
    assert any(
        transaction["description"] == "SALARY PAYMENT EMPLOYER"
        for transaction in created_transactions
    )
    assert any(transaction["type"] == "credit" for transaction in created_transactions)
    assert any(transaction["type"] == "debit" for transaction in created_transactions)
    assert len(weekly_counts) == MIN_HISTORY_WEEKS
    assert min(weekly_counts.values()) >= MIN_TRANSACTIONS_PER_WEEK
