from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes.auth import get_current_admin_user, get_current_user, utcnow
from app.core.config import Settings, get_settings
from app.db import SiteDirectoryEntry, User, get_db

router = APIRouter(prefix="/directory/sites")
admin_router = APIRouter(prefix="/admin/directory/sites")


class DirectorySiteSummary(BaseModel):
    id: str
    slug: str
    name: str
    description: str | None
    base_url: str
    icon: str | None
    required_role: str | None
    is_enabled: bool
    display_order: int


class DirectorySiteListResponse(BaseModel):
    sites: list[DirectorySiteSummary]


class DirectorySiteRequest(BaseModel):
    slug: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    base_url: str = Field(min_length=1, max_length=500)
    icon: str | None = Field(default=None, max_length=100)
    required_role: str | None = Field(default=None, max_length=100)
    is_enabled: bool = True
    display_order: int = 0


def serialize_site(site: SiteDirectoryEntry) -> DirectorySiteSummary:
    return DirectorySiteSummary(
        id=site.id,
        slug=site.slug,
        name=site.name,
        description=site.description,
        base_url=site.base_url,
        icon=site.icon,
        required_role=site.required_role,
        is_enabled=site.is_enabled,
        display_order=site.display_order,
    )


def ensure_default_sites(db: Session, settings: Settings) -> None:
    if db.scalar(select(SiteDirectoryEntry.id).limit(1)) is not None:
        return
    now = utcnow()
    db.add_all(
        [
            SiteDirectoryEntry(
                slug="goals",
                name="Goal Tracker",
                description="Track goals, metrics, dashboards, and progress widgets.",
                base_url=settings.goals_base_url,
                icon="pi pi-flag",
                display_order=10,
                created_at=now,
                updated_at=now,
            ),
            SiteDirectoryEntry(
                slug="money-planner",
                name="Fluffynomics",
                description="Track accounts, expenses, contracts, investments, and net worth.",
                base_url=settings.money_planner_base_url,
                icon="pi pi-wallet",
                display_order=20,
                created_at=now,
                updated_at=now,
            ),
        ]
    )
    db.commit()


def visible_to_user(site: SiteDirectoryEntry, user: User) -> bool:
    if not site.is_enabled:
        return False
    if site.required_role is None:
        return True
    if site.required_role == "admin":
        return user.is_admin
    return False


@router.get("", response_model=DirectorySiteListResponse)
def list_directory_sites(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DirectorySiteListResponse:
    ensure_default_sites(db, settings)
    sites = list(db.scalars(select(SiteDirectoryEntry).order_by(SiteDirectoryEntry.display_order.asc())))
    visible_sites = [serialize_site(site) for site in sites if visible_to_user(site, user)]
    return DirectorySiteListResponse(sites=visible_sites)


@admin_router.get("", response_model=DirectorySiteListResponse)
def admin_list_directory_sites(
    _admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DirectorySiteListResponse:
    ensure_default_sites(db, settings)
    sites = list(db.scalars(select(SiteDirectoryEntry).order_by(SiteDirectoryEntry.display_order.asc())))
    return DirectorySiteListResponse(sites=[serialize_site(site) for site in sites])


@admin_router.post("", response_model=DirectorySiteSummary, status_code=status.HTTP_201_CREATED)
def admin_create_directory_site(
    payload: DirectorySiteRequest,
    _admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> DirectorySiteSummary:
    if db.scalar(select(SiteDirectoryEntry.id).where(SiteDirectoryEntry.slug == payload.slug)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Directory site already exists.")
    now = utcnow()
    site = SiteDirectoryEntry(**payload.model_dump(), created_at=now, updated_at=now)
    db.add(site)
    db.commit()
    db.refresh(site)
    return serialize_site(site)


@admin_router.patch("/{site_id}", response_model=DirectorySiteSummary)
def admin_update_directory_site(
    site_id: str,
    payload: DirectorySiteRequest,
    _admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> DirectorySiteSummary:
    site = db.get(SiteDirectoryEntry, site_id)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Directory site not found.")
    for key, value in payload.model_dump().items():
        setattr(site, key, value)
    site.updated_at = utcnow()
    db.commit()
    db.refresh(site)
    return serialize_site(site)


@admin_router.delete("/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_directory_site(
    site_id: str,
    _admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    site = db.get(SiteDirectoryEntry, site_id)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Directory site not found.")
    db.delete(site)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
