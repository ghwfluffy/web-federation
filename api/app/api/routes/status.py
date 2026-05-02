from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app import __version__
from app.core.config import get_settings
from app.db.session import check_database

router = APIRouter(prefix="/status")


class StatusResponse(BaseModel):
    status: str
    app_name: str
    app_version: str
    app_base_path: str
    database: str


@router.get("", response_model=StatusResponse)
def get_status() -> StatusResponse:
    settings = get_settings()
    database_status = "ok" if check_database() else "unavailable"
    return StatusResponse(
        status="ok" if database_status == "ok" else "degraded",
        app_name=settings.app_name,
        app_version=__version__,
        app_base_path=settings.normalized_app_base_path,
        database=database_status,
    )
