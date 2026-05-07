from __future__ import annotations

from collections.abc import Generator
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_db
from app.api.v1 import bank_statements
from app.db.models import Base, UploadedStatement
from app.main import app
from app.services import (
    aggregation_service,
    bank_statement_service,
    categorisation_service,
    risk_service,
)
from app.storage import transactions


def test_complete_api_flow(monkeypatch) -> None:
    object_store = configure_fake_object_storage(monkeypatch)
    configure_fake_cache(monkeypatch)

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    try:
        health_response = client.get("/health")
        assert health_response.status_code == 200
        assert health_response.json() == {"status": "ok"}

        upload_response = client.post(
            "/api/v1/bank-statement/uplaod",
            data={"bank_name": "Capitec"},
            files={
                "file": (
                    "statement.pdf",
                    b"%PDF-1.4 simulated bank statement",
                    "application/pdf",
                )
            },
        )
        assert upload_response.status_code == 201
        upload_payload = upload_response.json()
        uploaded_statement = upload_payload["uploaded_statement"]
        statement_id = uploaded_statement["id"]

        assert uploaded_statement["bank_name"] == "Capitec"
        assert uploaded_statement["object_key"] == f"input/{statement_id}/statement.pdf"
        assert upload_payload["download_url"] == (
            f"http://testserver/api/v1/bank-statement/{statement_id}/download"
        )
        assert upload_payload["message"] == (
            "Bank statement uploaded successfully and processed with simulated OCR."
        )
        assert f"input/{statement_id}/statement.pdf" in object_store
        assert f"input/{statement_id}/transactions.json" in object_store

        with testing_session_local() as db:
            saved_statement = db.scalar(
                select(UploadedStatement).where(
                    UploadedStatement.id == UUID(statement_id)
                )
            )
        assert saved_statement is not None
        assert saved_statement.bank_name == "Capitec"
        assert saved_statement.object_key == uploaded_statement["object_key"]

        download_response = client.get(
            f"/api/v1/bank-statement/{statement_id}/download"
        )
        assert download_response.status_code == 200
        assert download_response.headers["content-type"] == "application/pdf"
        assert download_response.content == b"%PDF-1.4 simulated bank statement"

        categories_response = client.get(f"/api/v1/accounts/{statement_id}/categories")
        assert categories_response.status_code == 200
        categories_payload = categories_response.json()
        assert categories_payload["statement_id"] == statement_id
        assert categories_payload["cached"] is False
        summary_by_category = {
            item["category"]: item for item in categories_payload["category_summary"]
        }
        assert summary_by_category["salary"]["transaction_count"] >= 1
        assert f"output/{statement_id}/categories.json" in object_store

        aggregation_response = client.get(
            f"/api/v1/accounts/{statement_id}/aggregation"
        )
        assert aggregation_response.status_code == 200
        aggregation_payload = aggregation_response.json()
        assert aggregation_payload["statement_id"] == statement_id
        assert aggregation_payload["cached"] is False
        assert aggregation_payload["total_income"] > 0
        assert aggregation_payload["total_expenses"] > 0
        assert aggregation_payload["transaction_count"] >= 98
        assert aggregation_payload["month_count"] >= 4
        assert aggregation_payload["average_monthly_income"] > 0
        assert aggregation_payload["average_monthly_expenses"] > 0
        assert "average_monthly_net_cashflow" in aggregation_payload
        assert "savings_rate" in aggregation_payload
        assert "risk_flags" in aggregation_payload
        assert aggregation_payload["risk_flags"]["salary_detected"] is True
        assert aggregation_payload["insights"]
        assert "net_amount" in aggregation_payload["category_breakdown"]["salary"]
        assert "savings_rate" in next(
            iter(aggregation_payload["monthly_summary"].values())
        )
        assert f"output/{statement_id}/aggregation.json" in object_store

        risk_response = client.get(f"/api/v1/accounts/{statement_id}/risk")
        assert risk_response.status_code == 200
        risk_payload = risk_response.json()
        assert risk_payload["statement_id"] == statement_id
        assert risk_payload["cached"] is False
        assert risk_payload["risk_band"] in {"LOW_RISK", "MEDIUM_RISK", "HIGH_RISK"}
        assert f"output/{statement_id}/risk.json" in object_store
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)


def configure_fake_object_storage(monkeypatch) -> dict:
    object_store = {}

    def upload_bytes_object(
        object_key: str,
        content: bytes,
        content_type: str,
    ) -> str:
        object_store[object_key] = content
        return object_key

    def upload_json_object(object_key: str, value: dict | list) -> str:
        object_store[object_key] = value
        return object_key

    def read_json_object(object_key: str) -> dict | list:
        return object_store[object_key]

    def read_bytes_object(object_key: str) -> bytes:
        return object_store[object_key]

    monkeypatch.setattr(transactions, "upload_json_object", upload_json_object)
    monkeypatch.setattr(transactions, "read_json_object", read_json_object)
    monkeypatch.setattr(
        bank_statement_service,
        "upload_bytes_object",
        upload_bytes_object,
    )
    monkeypatch.setattr(bank_statements, "read_bytes_object", read_bytes_object)
    for service in (
        categorisation_service,
        aggregation_service,
        risk_service,
    ):
        monkeypatch.setattr(service, "upload_json_object", upload_json_object)

    return object_store


def configure_fake_cache(monkeypatch) -> None:
    cache_values = {}

    def get_cache(key: str) -> dict | None:
        return cache_values.get(key)

    def set_cache(key: str, value: dict, ttl_seconds: int = 3600) -> None:
        cache_values[key] = value

    for service in (
        categorisation_service,
        aggregation_service,
        risk_service,
    ):
        monkeypatch.setattr(service, "get_cache", get_cache)
        monkeypatch.setattr(service, "set_cache", set_cache)
