from __future__ import annotations

from fastapi.testclient import TestClient


def test_healthz(client: TestClient) -> None:
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_status_endpoint_returns_app_metadata(client: TestClient) -> None:
    response = client.get("/api/v1/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["app_name"] == "Central Auth"
    assert payload["app_base_path"] in {"", "/auth", "/ghwidx", "/index"}
    assert payload["database"] in {"ok", "unavailable"}
