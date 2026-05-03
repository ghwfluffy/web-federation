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


def test_welcome_phrase_endpoint_returns_phrase(client: TestClient) -> None:
    response = client.get("/api/v1/welcome/phrase")

    assert response.status_code == 200
    phrase = response.json()["phrase"]
    assert isinstance(phrase, str)
    assert "Ghw" in phrase


def test_api_errors_use_stable_envelope(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me", headers={"X-Request-ID": "test-request"})

    assert response.status_code == 401
    assert response.headers["X-Request-ID"] == "test-request"
    assert response.json() == {
        "error": {
            "code": "http_401",
            "message": "Not authenticated.",
            "field_errors": [],
            "request_id": "test-request",
        }
    }
