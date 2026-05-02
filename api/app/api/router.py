from __future__ import annotations

from fastapi import APIRouter

from app.api.routes.status import router as status_router

api_router = APIRouter()
api_router.include_router(status_router, tags=["status"])
