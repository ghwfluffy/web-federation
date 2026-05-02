from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.routes.auth import get_current_admin_user
from app.core.config import ROOT_DIR, Settings, get_settings
from app.db import User, get_db
from app.services.audit import record_audit_event

router = APIRouter(prefix="/admin/backups")


class BackupManifest(BaseModel):
    filename: str
    source: str
    created_at: str
    size_bytes: int
    sha256: str


class BackupListResponse(BaseModel):
    backups: list[BackupManifest]


def configured_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return ROOT_DIR / path


def read_backup_manifests(backup_dir: Path) -> list[BackupManifest]:
    if not backup_dir.exists():
        return []
    manifests: list[BackupManifest] = []
    for manifest_path in backup_dir.glob("*.json"):
        try:
            manifest = BackupManifest.model_validate(json.loads(manifest_path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError, ValueError):
            continue
        manifests.append(manifest)
    return sorted(manifests, key=lambda item: item.created_at, reverse=True)


@router.get("", response_model=BackupListResponse)
def list_backups(
    _admin: Annotated[User, Depends(get_current_admin_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> BackupListResponse:
    return BackupListResponse(backups=read_backup_manifests(configured_path(settings.backup_dir)))


@router.post("", response_model=BackupManifest, status_code=status.HTTP_201_CREATED)
def create_backup(
    admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> BackupManifest:
    script_path = configured_path(settings.backup_script_path)
    if not script_path.exists():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Backup script not found.",
        )

    backup_dir = configured_path(settings.backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(
        {
            "BACKUP_DIR": str(backup_dir),
            "POSTGRES_HOST": settings.postgres_host,
            "POSTGRES_PORT": str(settings.postgres_port),
            "POSTGRES_USER": settings.postgres_user,
            "POSTGRES_PASSWORD": settings.postgres_password,
            "POSTGRES_DB": settings.postgres_db,
        }
    )
    try:
        result = subprocess.run(
            [str(script_path), "manual"],
            check=True,
            capture_output=True,
            env=env,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Backup failed.") from exc

    dump_path = Path(result.stdout.strip().splitlines()[-1])
    manifest_path = dump_path.with_suffix(".json")
    if not manifest_path.exists():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Backup manifest not found.",
        )
    manifest = BackupManifest.model_validate(json.loads(manifest_path.read_text(encoding="utf-8")))
    record_audit_event(
        db,
        event_type="backup.create",
        message="Manual backup created.",
        actor=admin,
        details={"filename": manifest.filename, "size_bytes": manifest.size_bytes},
    )
    db.commit()
    return manifest
