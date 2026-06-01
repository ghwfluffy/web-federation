from __future__ import annotations

from fastapi.testclient import TestClient

from tests.test_auth_api import bootstrap_admin


def test_directory_defaults_are_visible_to_authenticated_users(isolated_client: TestClient) -> None:
    bootstrap_admin(isolated_client)

    response = isolated_client.get("/api/v1/directory/sites")

    assert response.status_code == 200
    payload = response.json()
    assert [site["slug"] for site in payload["sites"]] == ["goals", "money-planner", "agent"]


def test_directory_defaults_backfill_missing_sites(isolated_client: TestClient) -> None:
    bootstrap_admin(isolated_client)

    create_response = isolated_client.post(
        "/api/v1/admin/directory/sites",
        json={
            "slug": "legacy",
            "name": "Legacy",
            "description": "Existing site from an older deployment.",
            "base_url": "/legacy",
            "icon": "pi pi-link",
            "required_role": None,
            "is_enabled": True,
            "display_order": 5,
        },
    )
    assert create_response.status_code == 201

    response = isolated_client.get("/api/v1/directory/sites")

    assert response.status_code == 200
    sites = response.json()["sites"]
    assert "legacy" in [site["slug"] for site in sites]
    assert {
        "slug": "agent",
        "name": "AI Assistant",
        "base_url": "/agent",
    }.items() <= next(site for site in sites if site["slug"] == "agent").items()


def test_admin_can_crud_directory_sites(isolated_client: TestClient) -> None:
    bootstrap_admin(isolated_client)

    create_response = isolated_client.post(
        "/api/v1/admin/directory/sites",
        json={
            "slug": "notes",
            "name": "Notes",
            "description": "Notes app",
            "base_url": "/notes",
            "icon": "pi pi-book",
            "required_role": None,
            "is_enabled": True,
            "display_order": 30,
        },
    )
    assert create_response.status_code == 201
    site_id = create_response.json()["id"]

    update_response = isolated_client.patch(
        f"/api/v1/admin/directory/sites/{site_id}",
        json={
            "slug": "notes",
            "name": "Notes",
            "description": "Notes app",
            "base_url": "/notes",
            "icon": "pi pi-book",
            "required_role": None,
            "is_enabled": False,
            "display_order": 30,
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["is_enabled"] is False

    delete_response = isolated_client.delete(f"/api/v1/admin/directory/sites/{site_id}")
    assert delete_response.status_code == 204
