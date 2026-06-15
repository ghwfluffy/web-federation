from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app
from tests.test_auth_api import bootstrap_admin


def override_mobile_settings(tmp_path: Path) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(
        app_env="test",
        app_base_path="",
        android_apk_dir=str(tmp_path),
    )


def test_android_app_metadata_requires_auth(isolated_client: TestClient, tmp_path: Path) -> None:
    override_mobile_settings(tmp_path)

    response = isolated_client.get("/api/v1/mobile/android-app")

    assert response.status_code == 401


def test_android_app_metadata_reports_missing_artifact(isolated_client: TestClient, tmp_path: Path) -> None:
    override_mobile_settings(tmp_path)
    bootstrap_admin(isolated_client)

    response = isolated_client.get("/api/v1/mobile/android-app")

    assert response.status_code == 200
    assert response.json() == {
        "available": False,
        "artifact": None,
        "version_name": None,
        "version_code": None,
        "built_at": None,
        "size_bytes": None,
        "download_url": None,
    }


def test_android_app_metadata_and_download_use_staged_artifact(
    isolated_client: TestClient,
    tmp_path: Path,
) -> None:
    override_mobile_settings(tmp_path)
    apk = tmp_path / "assistant-debug.apk"
    apk.write_bytes(b"debug apk")
    (tmp_path / "assistant-debug.json").write_text(
        (
            '{"artifact":"assistant-debug.apk","versionName":"0.2.0",'
            '"versionCode":2,"builtAt":"2026-06-14T00:00:00Z"}'
        ),
        encoding="utf-8",
    )
    bootstrap_admin(isolated_client)

    metadata = isolated_client.get("/api/v1/mobile/android-app")

    assert metadata.status_code == 200
    assert metadata.json() == {
        "available": True,
        "artifact": "assistant-debug.apk",
        "version_name": "0.2.0",
        "version_code": 2,
        "built_at": "2026-06-14T00:00:00Z",
        "size_bytes": 9,
        "download_url": "/api/v1/mobile/android-app/download",
    }

    download = isolated_client.get("/api/v1/mobile/android-app/download")

    assert download.status_code == 200
    assert download.headers["content-type"] == "application/vnd.android.package-archive"
    assert download.content == b"debug apk"
