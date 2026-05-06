from __future__ import annotations

import asyncio
from collections.abc import Generator
from datetime import datetime, timezone
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_db
from app.api.v1 import bank_statements
from app.db.models import BankStatement, Base, User
from app.main import app
from app.services import bank_statement_service


def test_upload_valid_pdf_creates_statement_record_and_clean_response(
    monkeypatch,
) -> None:
    generated_transaction_keys = []
    session_local = configure_test_app(monkeypatch)
    monkeypatch.setattr(
        bank_statement_service,
        "upload_statement_pdf",
        lambda user_id, statement_id, file, content: (
            f"input/{user_id}/{statement_id}.pdf"
        ),
    )
    monkeypatch.setattr(
        bank_statement_service,
        "write_starter_transactions",
        lambda statement_id: generated_transaction_keys.append(
            f"output/{statement_id}/transactions.json"
        )
        or generated_transaction_keys[-1],
    )

    client = TestClient(app)
    try:
        response = client.post(
            "/api/v1/bank-statements/upload",
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
        assert payload["file_url"] == f"input/{payload['user_id']}/{payload['id']}.pdf"
        assert payload["bank_statement_pdf_download_url"] == (
            f"http://testserver/api/v1/bank-statements/{payload['id']}/download"
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
        assert generated_transaction_keys == [
            f"output/{statement_id}/transactions.json"
        ]
    finally:
        app.dependency_overrides.clear()


def test_upload_rejects_non_pdf_file(monkeypatch) -> None:
    configure_test_app(monkeypatch)
    client = TestClient(app)

    try:
        response = client.post(
            "/api/v1/bank-statements/upload",
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


def test_download_bank_statement_pdf_streams_minio_object(monkeypatch) -> None:
    session_local = configure_test_app(monkeypatch)
    statement_id = UUID("550e8400-e29b-41d4-a716-446655440000")
    user_id = UUID("650e8400-e29b-41d4-a716-446655440000")
    file_url = f"input/{user_id}/{statement_id}.pdf"
    read_calls = []
    monkeypatch.setattr(
        bank_statements,
        "read_bytes_object",
        lambda object_key: read_calls.append(object_key)
        or b"%PDF-1.4 simulated statement",
    )

    with session_local() as db:
        db.add(User(id=user_id, name="Lucas George"))
        db.flush()
        db.add(
            BankStatement(
                id=statement_id,
                user_id=user_id,
                bank_name="FNB Statement April 2026",
                file_url=file_url,
            )
        )
        db.commit()

    client = TestClient(app)
    try:
        response = client.get(f"/api/v1/bank-statements/{statement_id}/download")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert response.content == b"%PDF-1.4 simulated statement"
        assert read_calls == [file_url]
    finally:
        app.dependency_overrides.clear()


def test_bank_statement_service_reuses_transaction_generation_flow(
    monkeypatch,
) -> None:
    calls = {}

    def fake_upload_statement_pdf(user_id, statement_id, file, content):
        calls["upload"] = {
            "user_id": user_id,
            "statement_id": statement_id,
            "content": content,
        }
        return f"input/{user_id}/{statement_id}.pdf"

    def fake_write_starter_transactions(statement_id):
        calls["write_starter_transactions"] = {"statement_id": statement_id}
        return f"output/{statement_id}/transactions.json"

    monkeypatch.setattr(
        bank_statement_service,
        "upload_statement_pdf",
        fake_upload_statement_pdf,
    )
    monkeypatch.setattr(
        bank_statement_service,
        "write_starter_transactions",
        fake_write_starter_transactions,
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

    assert (
        calls["upload"]["statement_id"]
        == calls["write_starter_transactions"]["statement_id"]
    )
    assert calls["upload"]["content"] == b"%PDF-1.4 simulated statement"
    assert db.committed is True
    assert len(db.added) == 2
    assert isinstance(db.added[0], User)
    assert db.added[0].name == "Lucas George"
    assert isinstance(db.added[1], BankStatement)
    assert db.added[1].bank_name == "FNB Statement April 2026"
    assert response.id == calls["upload"]["statement_id"]
    assert response.file_url.startswith("input/")


def configure_test_app(monkeypatch):
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

    def flush(self) -> None:
        pass

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def refresh(self, item: object) -> None:
        item.created_at = datetime(2026, 5, 5, tzinfo=timezone.utc)  # noqa: UP017
        if hasattr(item, "updated_at"):
            item.updated_at = datetime(2026, 5, 5, tzinfo=timezone.utc)  # noqa: UP017
