from __future__ import annotations

import base64
import hashlib
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from app.db.models import OAuthClient


def bootstrap_admin(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/bootstrap",
        json={"username": "admin", "password": "supersafepassword"},
    )
    assert response.status_code == 201


def code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def seed_oauth_client(client: TestClient) -> None:
    SessionLocal = client.app.state.testing_session_local
    with SessionLocal() as db:
        db.add(
            OAuthClient(
                client_id="goals",
                name="Goal Tracker",
                redirect_uris=["http://goals.local/auth/callback"],
                allowed_origins=["http://goals.local"],
            )
        )
        db.commit()


def authorize(client: TestClient, *, verifier: str = "verifier") -> str:
    response = client.get(
        "/oauth/authorize",
        params={
            "response_type": "code",
            "client_id": "goals",
            "redirect_uri": "http://goals.local/auth/callback",
            "scope": "openid profile",
            "state": "abc",
            "code_challenge": code_challenge(verifier),
            "code_challenge_method": "S256",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    location = response.headers["location"]
    assert location.startswith("http://goals.local/auth/callback")
    parsed = parse_qs(urlparse(location).query)
    assert parsed["state"] == ["abc"]
    return parsed["code"][0]


def test_oauth_discovery_and_authorization_code_flow(isolated_client: TestClient) -> None:
    bootstrap_admin(isolated_client)
    seed_oauth_client(isolated_client)

    discovery_response = isolated_client.get("/.well-known/openid-configuration")
    assert discovery_response.status_code == 200
    assert discovery_response.json()["authorization_endpoint"].endswith("/oauth/authorize")

    code = authorize(isolated_client)
    token_response = isolated_client.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "client_id": "goals",
            "code": code,
            "redirect_uri": "http://goals.local/auth/callback",
            "code_verifier": "verifier",
        },
    )
    assert token_response.status_code == 200
    token_payload = token_response.json()
    assert token_payload["token_type"] == "Bearer"

    userinfo_response = isolated_client.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {token_payload['access_token']}"},
    )
    assert userinfo_response.status_code == 200
    assert userinfo_response.json()["preferred_username"] == "admin"


def test_oauth_rejects_reused_code_and_invalid_redirect(isolated_client: TestClient) -> None:
    bootstrap_admin(isolated_client)
    seed_oauth_client(isolated_client)

    invalid_redirect_response = isolated_client.get(
        "/oauth/authorize",
        params={
            "response_type": "code",
            "client_id": "goals",
            "redirect_uri": "http://evil.local/callback",
            "scope": "openid profile",
            "code_challenge": code_challenge("verifier"),
            "code_challenge_method": "S256",
        },
    )
    assert invalid_redirect_response.status_code == 400

    code = authorize(isolated_client)
    form = {
        "grant_type": "authorization_code",
        "client_id": "goals",
        "code": code,
        "redirect_uri": "http://goals.local/auth/callback",
        "code_verifier": "verifier",
    }
    assert isolated_client.post("/oauth/token", data=form).status_code == 200
    assert isolated_client.post("/oauth/token", data=form).status_code == 400
