from __future__ import annotations

from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.backups import router as backups_router
from app.api.routes.directory import admin_router as directory_admin_router
from app.api.routes.directory import router as directory_router
from app.api.routes.registration_codes import router as registration_codes_router
from app.api.routes.status import router as status_router
from app.api.routes.users import router as users_router

api_router = APIRouter()
api_router.include_router(auth_router, tags=["auth"])
api_router.include_router(backups_router, tags=["backups"])
api_router.include_router(directory_admin_router, tags=["directory"])
api_router.include_router(directory_router, tags=["directory"])
api_router.include_router(registration_codes_router, tags=["registration-codes"])
api_router.include_router(status_router, tags=["status"])
api_router.include_router(users_router, tags=["users"])
