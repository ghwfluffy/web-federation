from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db import OAuthClient, SiteDirectoryEntry


@dataclass(frozen=True)
class DefaultOAuthClient:
    client_id: str
    name: str
    app_base_url: str
    callback_path: str


def utcnow() -> datetime:
    return datetime.now(tz=UTC)


def public_app_base_url(settings: Settings, app_base_url: str) -> str:
    stripped = app_base_url.rstrip("/")
    if stripped.startswith("http://") or stripped.startswith("https://"):
        return stripped
    if stripped == "":
        return settings.public_origin
    normalized = stripped if stripped.startswith("/") else f"/{stripped}"
    return f"{settings.public_origin}{normalized}"


def default_oauth_clients(settings: Settings) -> list[DefaultOAuthClient]:
    return [
        DefaultOAuthClient(
            client_id="goals",
            name="Goal Tracker",
            app_base_url=settings.goals_base_url,
            callback_path="/api/v1/auth/oauth/callback",
        ),
        DefaultOAuthClient(
            client_id="money-planner",
            name="Fluffynomics",
            app_base_url=settings.money_planner_base_url,
            callback_path="/api/auth/oauth/callback",
        ),
        DefaultOAuthClient(
            client_id="agent",
            name="AI Assistant",
            app_base_url=settings.agent_base_url,
            callback_path="/api/v1/auth/oauth/callback",
        ),
        DefaultOAuthClient(
            client_id="apartment-gate",
            name="Apartment Gate",
            app_base_url=settings.apartment_gate_base_url,
            callback_path="/auth/oauth/callback",
        ),
    ]


def ensure_default_oauth_clients(db: Session, settings: Settings) -> dict[str, OAuthClient]:
    now = utcnow()
    clients_by_client_id = {
        client.client_id: client
        for client in db.scalars(
            select(OAuthClient).where(
                OAuthClient.client_id.in_([client.client_id for client in default_oauth_clients(settings)])
            )
        )
    }
    for default_client in default_oauth_clients(settings):
        base_url = public_app_base_url(settings, default_client.app_base_url)
        redirect_uris = [f"{base_url}{default_client.callback_path}"]
        allowed_origins = [settings.public_origin]
        client = clients_by_client_id.get(default_client.client_id)
        if client is not None:
            continue
        client = OAuthClient(
            client_id=default_client.client_id,
            name=default_client.name,
            redirect_uris=redirect_uris,
            allowed_origins=allowed_origins,
            is_enabled=True,
            created_at=now,
            updated_at=now,
        )
        db.add(client)
        clients_by_client_id[default_client.client_id] = client
    db.flush()
    return clients_by_client_id


def ensure_default_sites(db: Session, settings: Settings) -> None:
    clients_by_client_id = ensure_default_oauth_clients(db, settings)
    now = utcnow()
    existing_slugs = set(db.scalars(select(SiteDirectoryEntry.slug)))
    default_entries = [
        SiteDirectoryEntry(
            slug="goals",
            name="Goal Tracker",
            description="Track goals, metrics, dashboards, and progress widgets.",
            base_url=settings.goals_base_url,
            icon="pi pi-flag",
            oauth_client_id=clients_by_client_id["goals"].id,
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
            oauth_client_id=clients_by_client_id["money-planner"].id,
            display_order=20,
            created_at=now,
            updated_at=now,
        ),
        SiteDirectoryEntry(
            slug="agent",
            name="AI Assistant",
            description="Run scheduled assistant tasks, mailbox workflows, and audited agent activity.",
            base_url=settings.agent_base_url,
            icon="pi pi-sparkles",
            oauth_client_id=clients_by_client_id["agent"].id,
            display_order=30,
            created_at=now,
            updated_at=now,
        ),
        SiteDirectoryEntry(
            slug="apartment-gate",
            name="Apartment Gate",
            description="Open apartment community gates and doors from a protected mobile app.",
            base_url=settings.apartment_gate_base_url,
            icon="pi pi-lock-open",
            oauth_client_id=clients_by_client_id["apartment-gate"].id,
            display_order=40,
            created_at=now,
            updated_at=now,
        ),
    ]
    db.add_all([entry for entry in default_entries if entry.slug not in existing_slugs])
