from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check_returns_ok() -> None:
    request_id = "test-request-id"
    response = client.get("/health", headers={"X-Request-ID": request_id})

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"] == request_id


def test_metrics_endpoint_exposes_prometheus_metrics() -> None:
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "api_requests_total" in response.text
    assert "api_request_duration_seconds" in response.text


def test_metrics_use_route_template_for_uuid_paths() -> None:
    statement_id = "1b475e51-4be0-4056-b9dd-1e308b2fcd2f"

    client.get(f"/api/v1/accounts/{statement_id}/aggregation")
    response = client.get("/metrics")

    assert 'path="/api/v1/accounts/{statement_id}/aggregation"' in response.text
    assert f'path="/api/v1/accounts/{statement_id}/aggregation"' not in response.text
