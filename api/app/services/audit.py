from __future__ import annotations

from sqlalchemy.orm import Session

from app.db import AuditEvent, User


def record_audit_event(
    db: Session,
    *,
    event_type: str,
    message: str,
    actor: User | None = None,
    details: dict[str, object] | None = None,
) -> None:
    db.add(
        AuditEvent(
            actor_user_id=actor.id if actor is not None else None,
            event_type=event_type,
            message=message,
            details=details or {},
        )
    )
