from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

ONE_BY_ONE_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


def bootstrap_admin(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/auth/bootstrap",
        json={"username": "admin", "password": "supersafepassword"},
    )
    assert response.status_code == 201
    return response.json()["user"]


def test_bootstrap_login_me_logout_flow(isolated_client: TestClient) -> None:
    status_response = isolated_client.get("/api/v1/auth/bootstrap-status")
    assert status_response.json() == {"bootstrap_required": True}

    user = bootstrap_admin(isolated_client)
    assert user["username"] == "admin"
    assert user["is_admin"] is True
    assert "auth_session" in isolated_client.cookies

    me_response = isolated_client.get("/api/v1/auth/me")
    assert me_response.status_code == 200
    assert me_response.json()["user"]["username"] == "admin"

    logout_response = isolated_client.post("/api/v1/auth/logout")
    assert logout_response.status_code == 204

    after_logout_response = isolated_client.get("/api/v1/auth/me")
    assert after_logout_response.status_code == 401


def test_registration_codes_allow_signup(isolated_client: TestClient) -> None:
    bootstrap_admin(isolated_client)

    code_response = isolated_client.post(
        "/api/v1/registration-codes",
        json={
            "description": "teammate",
            "expires_at": (datetime.now(tz=UTC) + timedelta(days=1)).isoformat(),
        },
    )
    assert code_response.status_code == 201
    raw_code = code_response.json()["code"]
    assert raw_code is not None

    isolated_client.post("/api/v1/auth/logout")
    register_response = isolated_client.post(
        "/api/v1/auth/register",
        json={"username": "member", "password": "supersafepassword", "registration_code": raw_code},
    )
    assert register_response.status_code == 201
    assert register_response.json()["user"]["username"] == "member"
    assert register_response.json()["user"]["is_admin"] is False


def test_admin_user_crud_and_last_admin_guard(isolated_client: TestClient) -> None:
    admin = bootstrap_admin(isolated_client)

    create_response = isolated_client.post(
        "/api/v1/users",
        json={
            "username": "member",
            "password": "supersafepassword",
            "display_name": "Member",
            "timezone": "America/Chicago",
            "is_admin": False,
            "is_disabled": False,
        },
    )
    assert create_response.status_code == 201
    member = create_response.json()

    demote_response = isolated_client.patch(
        f"/api/v1/users/{admin['id']}",
        json={
            "display_name": None,
            "timezone": "America/Chicago",
            "is_admin": False,
            "is_disabled": False,
        },
    )
    assert demote_response.status_code == 422

    delete_response = isolated_client.delete(f"/api/v1/users/{member['id']}")
    assert delete_response.status_code == 204


def test_profile_update_password_and_avatar(isolated_client: TestClient) -> None:
    bootstrap_admin(isolated_client)

    profile_response = isolated_client.patch(
        "/api/v1/users/me",
        json={"display_name": "Taylor", "timezone": "America/Los_Angeles"},
    )
    assert profile_response.status_code == 200
    assert profile_response.json()["display_name"] == "Taylor"

    avatar_response = isolated_client.post(
        "/api/v1/users/me/avatar",
        files={"avatar": ("avatar.png", ONE_BY_ONE_PNG, "image/png")},
    )
    assert avatar_response.status_code == 200
    assert avatar_response.json()["avatar_url"] is not None

    password_response = isolated_client.post(
        "/api/v1/users/me/change-password",
        json={"current_password": "supersafepassword", "new_password": "newpassword1"},
    )
    assert password_response.status_code == 200

    me_response = isolated_client.get("/api/v1/auth/me")
    assert me_response.status_code == 401
