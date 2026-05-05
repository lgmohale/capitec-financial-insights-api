from __future__ import annotations

import asyncio
from collections.abc import Generator
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_db
from app.db.models import BankStatement, Base
from app.main import app
from app.schemas.bank_accounts import (
    LinkBankAccountResponse,
    LinkedAccountMetadata,
    UserMetadata,
)
from app.services import bank_statement_service
from app.storage import transactions


def test_upload_valid_pdf_creates_statement_record_and_clean_response(
    tmp_path,
    monkeypatch,
) -> None:
    input_dir = tmp_path / "data" / "input"
    session_local = configure_test_app(monkeypatch, input_dir)
    monkeypatch.setattr(
        bank_statement_service,
        "upload_statement_pdf",
        lambda user_id, statement_id, file, content: (
            f"bank-statements/{user_id}/{statement_id}.pdf"
        ),
    )

    client = TestClient(app)
    try:
        response = client.post(
            "/api/v1/bank-accounts/statement-upload",
            data={
                "user_names": "Lucas George",
                "bank_name": "FNB Statement April 2026",
            },
            files={
                "file": (
                    "statement.pdf",
                    b"%PDF-1.4 simulated statement",
                    "application/pdf",
                )
            },
        )

        assert response.status_code == 201
        payload = response.json()
        statement_id = UUID(payload["id"])
        assert UUID(payload["user_id"])
        assert payload["bank_name"] == "FNB Statement April 2026"
        assert payload["file_url"] == (
            f"bank-statements/{payload['user_id']}/{payload['id']}.pdf"
        )
        assert payload["message"] == bank_statement_service.SUCCESS_MESSAGE
        assert "transaction_file_path" not in payload
        assert "data/input" not in response.text
        assert "data/output" not in response.text

        with session_local() as db:
            bank_statement = db.scalar(
                select(BankStatement).where(BankStatement.id == statement_id)
            )

        assert bank_statement is not None
        assert str(bank_statement.user_id) == payload["user_id"]
        assert bank_statement.bank_name == payload["bank_name"]
        assert bank_statement.file_url == payload["file_url"]
        assert (input_dir / f"{statement_id}.json").exists()
    finally:
        app.dependency_overrides.clear()


def test_upload_rejects_non_pdf_file(tmp_path, monkeypatch) -> None:
    configure_test_app(monkeypatch, tmp_path / "data" / "input")
    client = TestClient(app)

    try:
        response = client.post(
            "/api/v1/bank-accounts/statement-upload",
            data={
                "user_names": "Lucas George",
                "bank_name": "FNB Statement April 2026",
            },
            files={
                "file": (
                    "statement.txt",
                    b"not a pdf",
                    "text/plain",
                )
            },
        )

        assert response.status_code == 400
        assert response.json() == {
            "detail": "Only PDF statement uploads are supported."
        }
    finally:
        app.dependency_overrides.clear()


def test_bank_statement_service_reuses_linked_account_generation_flow(
    monkeypatch,
) -> None:
    calls = {}

    def fake_upload_statement_pdf(user_id, statement_id, file, content):
        calls["upload"] = {
            "user_id": user_id,
            "statement_id": statement_id,
            "content": content,
        }
        return f"bank-statements/{user_id}/{statement_id}.pdf"

    def fake_create_linked_account(name, bank_name, db, user_id, linked_account_id):
        calls["create_linked_account"] = {
            "name": name,
            "bank_name": bank_name,
            "db": db,
            "user_id": user_id,
            "linked_account_id": linked_account_id,
        }
        return (
            LinkBankAccountResponse(
                user=UserMetadata(
                    id=user_id,
                    name=name,
                    created_at=datetime(2026, 5, 5, tzinfo=timezone.utc),  # noqa: UP017
                    updated_at=datetime(2026, 5, 5, tzinfo=timezone.utc),  # noqa: UP017
                ),
                linked_account=LinkedAccountMetadata(
                    user_id=user_id,
                    id=linked_account_id,
                    bank_name=bank_name,
                    created_at=datetime(2026, 5, 5, tzinfo=timezone.utc),  # noqa: UP017
                ),
            ),
            Path(f"data/input/{linked_account_id}.json"),
        )

    monkeypatch.setattr(
        bank_statement_service,
        "upload_statement_pdf",
        fake_upload_statement_pdf,
    )
    monkeypatch.setattr(
        bank_statement_service,
        "create_linked_account",
        fake_create_linked_account,
    )

    db = FakeSession()
    file = FakeUploadFile(
        filename="statement.pdf",
        content=b"%PDF-1.4 simulated statement",
    )

    response = asyncio.run(
        bank_statement_service.upload_and_process_bank_statement(
            user_names="Lucas George",
            bank_name="FNB Statement April 2026",
            file=file,
            db=db,
        )
    )

    assert calls["upload"]["user_id"] == calls["create_linked_account"]["user_id"]
    assert (
        calls["upload"]["statement_id"]
        == calls["create_linked_account"]["linked_account_id"]
    )
    assert calls["create_linked_account"]["name"] == "Lucas George"
    assert calls["create_linked_account"]["bank_name"] == "FNB Statement April 2026"
    assert calls["upload"]["content"] == b"%PDF-1.4 simulated statement"
    assert db.committed is True
    assert len(db.added) == 1
    assert isinstance(db.added[0], BankStatement)
    assert response.id == calls["upload"]["statement_id"]
    assert response.file_url.startswith("bank-statements/")


def configure_test_app(monkeypatch, input_dir: Path):
    monkeypatch.setattr(transactions, "INPUT_DIR", input_dir)
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    def override_get_db() -> Generator[Session, None, None]:
        db = session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return session_local


class FakeUploadFile:
    def __init__(self, filename: str, content: bytes) -> None:
        self.filename = filename
        self.content_type = "application/pdf"
        self.content = content

    async def read(self) -> bytes:
        return self.content


class FakeSession:
    def __init__(self) -> None:
        self.added = []
        self.committed = False
        self.rolled_back = False

    def add(self, item: object) -> None:
        self.added.append(item)

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def refresh(self, item: object) -> None:
        item.created_at = datetime(2026, 5, 5, tzinfo=timezone.utc)  # noqa: UP017
