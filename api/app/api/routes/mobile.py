from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.api.routes.auth import get_current_user
from app.core.config import Settings, get_settings
from app.db import User

router = APIRouter(prefix="/mobile/android-app")


class AndroidAppMetadata(BaseModel):
    available: bool
    artifact: str | None = None
    version_name: str | None = None
    version_code: int | None = None
    built_at: str | None = None
    size_bytes: int | None = None
    download_url: str | None = None


def apk_path(settings: Settings) -> Path | None:
    if settings.android_apk_dir.strip() == "":
        return None
    return Path(settings.android_apk_dir) / settings.android_apk_filename


def metadata_path(settings: Settings) -> Path | None:
    if settings.android_apk_dir.strip() == "":
        return None
    return Path(settings.android_apk_dir) / settings.android_apk_metadata_filename


def read_metadata(settings: Settings) -> dict[str, Any]:
    path = metadata_path(settings)
    if path is None or not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


@router.get("", response_model=AndroidAppMetadata)
def get_android_app_metadata(
    _user: Annotated[User, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AndroidAppMetadata:
    path = apk_path(settings)
    if path is None or not path.is_file():
        return AndroidAppMetadata(available=False)
    stat = path.stat()
    metadata = read_metadata(settings)
    return AndroidAppMetadata(
        available=True,
        artifact=str(metadata.get("artifact") or settings.android_apk_filename),
        version_name=str(metadata.get("versionName") or "") or None,
        version_code=metadata.get("versionCode") if isinstance(metadata.get("versionCode"), int) else None,
        built_at=str(metadata.get("builtAt") or "") or None,
        size_bytes=stat.st_size,
        download_url=(
            f"{settings.normalized_app_base_path}{settings.api_v1_prefix}/mobile/android-app/download"
        ),
    )


@router.get("/download")
def download_android_app(
    _user: Annotated[User, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> FileResponse:
    path = apk_path(settings)
    if path is None or not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Android app artifact is not available.",
        )
    return FileResponse(
        path,
        media_type="application/vnd.android.package-archive",
        filename=settings.android_apk_filename,
    )
