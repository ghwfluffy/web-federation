from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.db import AuditEvent
from app.main import app
from tests.test_auth_api import bootstrap_admin


def override_settings(settings: Settings) -> None:
    app.dependency_overrides[get_settings] = lambda: settings


def test_admin_can_list_and_create_backups(isolated_client: TestClient, tmp_path: Path) -> None:
    bootstrap_admin(isolated_client)
    script_path = tmp_path / "create_backup.sh"
    script_path.write_text(
        """#!/bin/sh
set -eu
mkdir -p "$BACKUP_DIR"
printf dump > "$BACKUP_DIR/manual.dump"
cat > "$BACKUP_DIR/manual.json" <<EOF
{"filename":"manual.dump","source":"manual","created_at":"20260502T000000Z","size_bytes":4,"sha256":"abc"}
EOF
printf '%s\n' "$BACKUP_DIR/manual.dump"
""",
        encoding="utf-8",
    )
    script_path.chmod(script_path.stat().st_mode | 0o111)
    override_settings(Settings(backup_dir=str(tmp_path / "backups"), backup_script_path=str(script_path)))

    create_response = isolated_client.post("/api/v1/admin/backups")
    assert create_response.status_code == 201
    assert create_response.json()["filename"] == "manual.dump"

    list_response = isolated_client.get("/api/v1/admin/backups")
    assert list_response.status_code == 200
    assert list_response.json()["backups"][0]["source"] == "manual"


def test_audit_events_are_written_for_identity_actions(isolated_client: TestClient) -> None:
    bootstrap_admin(isolated_client)
    SessionLocal = isolated_client.app.state.testing_session_local
    with SessionLocal() as db:
        event_types = {row.event_type for row in db.query(AuditEvent).all()}
    assert {"auth.bootstrap"}.issubset(event_types)


def test_production_rejects_unsafe_secret_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SESSION_KEY", "changeme")
    monkeypatch.setenv("POSTGRES_PASSWORD", "supersecure")
    monkeypatch.setenv("PUBLIC_URL", "http://localhost:8090")
    get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="Unsafe production configuration"):
            get_settings()
    finally:
        get_settings.cache_clear()
