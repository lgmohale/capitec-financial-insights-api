from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_db
from app.db.models import Base
from app.main import app
from app.services import (
    aggregation_service,
    categorisation_service,
    recommendation_service,
    risk_service,
)
from app.storage import transactions


def test_complete_api_flow(tmp_path, monkeypatch) -> None:
    input_dir = tmp_path / "data" / "input"
    output_dir = tmp_path / "data" / "output"
    configure_temp_storage(monkeypatch, input_dir, output_dir)
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

        link_response = client.post(
            "/api/v1/bank-accounts/link",
            json={"name": "Lucas George", "bank_name": "Capitec"},
        )
        assert link_response.status_code == 201
        link_payload = link_response.json()
        account_uuid = link_payload["linked_account"]["uuid"]
        assert link_payload["user"]["name"] == "Lucas George"
        assert link_payload["linked_account"]["bank_name"] == "Capitec"
        assert (input_dir / f"{account_uuid}.json").exists()

        categories_response = client.get(f"/api/v1/accounts/{account_uuid}/categories")
        assert categories_response.status_code == 200
        categories_payload = categories_response.json()
        assert categories_payload["cached"] is False
        assert categories_payload["category_summary"]["salary"] >= 1
        assert Path(categories_payload["output_file_path"]).exists()

        aggregation_response = client.get(
            f"/api/v1/accounts/{account_uuid}/aggregation"
        )
        assert aggregation_response.status_code == 200
        aggregation_payload = aggregation_response.json()
        assert aggregation_payload["cached"] is False
        assert aggregation_payload["total_income"] > 0
        assert aggregation_payload["total_expenses"] > 0
        assert aggregation_payload["transaction_count"] >= 98
        assert aggregation_payload["month_count"] >= 4
        assert Path(aggregation_payload["output_file_path"]).exists()

        risk_response = client.get(f"/api/v1/accounts/{account_uuid}/risk")
        assert risk_response.status_code == 200
        risk_payload = risk_response.json()
        assert risk_payload["cached"] is False
        assert risk_payload["risk_band"] in {"LOW_RISK", "MEDIUM_RISK", "HIGH_RISK"}
        assert Path(risk_payload["output_file_path"]).exists()

        recommendations_response = client.get(
            f"/api/v1/accounts/{account_uuid}/recommendations"
        )
        assert recommendations_response.status_code == 200
        recommendations_payload = recommendations_response.json()
        assert recommendations_payload["cached"] is False
        assert recommendations_payload["recommendations"]
        assert Path(recommendations_payload["output_file_path"]).exists()

        insights_response = client.get(
            f"/api/v1/accounts/{account_uuid}/financial-insights"
        )
        assert insights_response.status_code == 200
        insights_payload = insights_response.json()
        assert insights_payload["account_uuid"] == account_uuid
        assert insights_payload["user"]["name"] == "Lucas George"
        assert insights_payload["linked_account"]["uuid"] == account_uuid
        assert insights_payload["aggregation"]["cached"] is True
        assert insights_payload["risk"]["cached"] is True
        assert insights_payload["recommendations"]["cached"] is True
        assert insights_payload["generated_at"]
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)


def configure_temp_storage(monkeypatch, input_dir: Path, output_dir: Path) -> None:
    monkeypatch.setattr(transactions, "INPUT_DIR", input_dir)
    monkeypatch.setattr(transactions, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(categorisation_service, "INPUT_DIR", input_dir)
    monkeypatch.setattr(categorisation_service, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(aggregation_service, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(risk_service, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(recommendation_service, "OUTPUT_DIR", output_dir)


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
