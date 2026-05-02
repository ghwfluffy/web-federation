from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.api.routes.oauth import metadata_router
from app.api.routes.oauth import router as oauth_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    root_path=settings.normalized_app_base_path,
)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)
app.include_router(metadata_router)
app.include_router(oauth_router)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
