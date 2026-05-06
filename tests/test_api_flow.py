from __future__ import annotations

from collections.abc import Generator
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_db
from app.db.models import BankStatement, Base
from app.main import app
from app.services import (
    aggregation_service,
    bank_statement_service,
    categorisation_service,
    recommendation_service,
    risk_service,
)
from app.storage import transactions


def test_complete_api_flow(tmp_path, monkeypatch) -> None:
    object_store = configure_fake_object_storage(monkeypatch)
    configure_fake_cache(monkeypatch)
    monkeypatch.setattr(
        bank_statement_service,
        "upload_statement_pdf",
        lambda user_id, statement_id, file, content: (
            f"input/{user_id}/{statement_id}.pdf"
        ),
    )

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
        assert upload_response.status_code == 201
        upload_payload = upload_response.json()
        account_id = upload_payload["id"]
        assert upload_payload["user_id"]
        assert upload_payload["bank_name"] == "FNB Statement April 2026"
        assert (
            upload_payload["file_url"]
            == f"input/{upload_payload['user_id']}/{account_id}.pdf"
        )
        assert upload_payload["message"] == (
            "Bank statement uploaded successfully and queued for processing."
        )
        expected_download_url = (
            f"http://testserver/api/v1/bank-statements/{account_id}/download"
        )
        assert (
            upload_payload["bank_statement_pdf_download_url"] == expected_download_url
        )
        assert "transaction_file_path" not in upload_payload
        assert f"output/{account_id}/transactions.json" in object_store
        with testing_session_local() as db:
            bank_statement = db.scalar(
                select(BankStatement).where(BankStatement.id == UUID(account_id))
            )
        assert bank_statement is not None
        assert str(bank_statement.user_id) == upload_payload["user_id"]
        assert bank_statement.bank_name == "FNB Statement April 2026"
        assert bank_statement.file_url == upload_payload["file_url"]

        categories_response = client.get(f"/api/v1/accounts/{account_id}/categories")
        assert categories_response.status_code == 200
        categories_payload = categories_response.json()
        assert categories_payload["cached"] is False
        summary_by_category = {
            item["category"]: item for item in categories_payload["category_summary"]
        }
        assert summary_by_category["salary"]["transaction_count"] >= 1
        assert categories_payload["bank_statement_pdf_download_url"] == (
            expected_download_url
        )
        assert f"output/{account_id}/categories.json" in object_store
        assert "output_object_key" not in categories_payload

        aggregation_response = client.get(f"/api/v1/accounts/{account_id}/aggregation")
        assert aggregation_response.status_code == 200
        aggregation_payload = aggregation_response.json()
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
        assert aggregation_payload["bank_statement_pdf_download_url"] == (
            expected_download_url
        )
        assert f"output/{account_id}/aggregation.json" in object_store
        assert "output_object_key" not in aggregation_payload

        risk_response = client.get(f"/api/v1/accounts/{account_id}/risk")
        assert risk_response.status_code == 200
        risk_payload = risk_response.json()
        assert risk_payload["cached"] is False
        assert risk_payload["risk_band"] in {"LOW_RISK", "MEDIUM_RISK", "HIGH_RISK"}
        assert risk_payload["bank_statement_pdf_download_url"] == expected_download_url
        assert f"output/{account_id}/risk.json" in object_store
        assert "output_object_key" not in risk_payload

        recommendations_response = client.get(
            f"/api/v1/accounts/{account_id}/recommendations"
        )
        assert recommendations_response.status_code == 200
        recommendations_payload = recommendations_response.json()
        assert recommendations_payload["cached"] is False
        assert recommendations_payload["recommendations"]
        assert recommendations_payload["bank_statement_pdf_download_url"] == (
            expected_download_url
        )
        assert f"output/{account_id}/recommendations.json" in object_store
        assert "output_object_key" not in recommendations_payload

        insights_response = client.get(
            f"/api/v1/accounts/{account_id}/financial-insights"
        )
        assert insights_response.status_code == 200
        insights_payload = insights_response.json()
        assert insights_payload["account_id"] == account_id
        assert insights_payload["user"]["name"] == "Lucas George"
        assert insights_payload["bank_statement"]["id"] == account_id
        assert insights_payload["aggregation"]["cached"] is True
        assert insights_payload["risk"]["cached"] is True
        assert insights_payload["recommendations"]["cached"] is True
        assert insights_payload["aggregation"]["bank_statement_pdf_download_url"] == (
            expected_download_url
        )
        assert insights_payload["generated_at"]
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)


def configure_fake_object_storage(monkeypatch) -> dict:
    object_store = {}

    def upload_json_object(object_key: str, value: dict | list) -> str:
        object_store[object_key] = value
        return object_key

    def read_json_object(object_key: str) -> dict | list:
        return object_store[object_key]

    monkeypatch.setattr(transactions, "upload_json_object", upload_json_object)
    monkeypatch.setattr(transactions, "read_json_object", read_json_object)
    for service in (
        categorisation_service,
        aggregation_service,
        risk_service,
        recommendation_service,
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
        recommendation_service,
    ):
        monkeypatch.setattr(service, "get_cache", get_cache)
        monkeypatch.setattr(service, "set_cache", set_cache)
