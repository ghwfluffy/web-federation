from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import (
    decode_signed_token,
    encode_signed_token,
    generate_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.db import AuthRefreshToken, AuthSession, RegistrationCode, User, get_db
from app.services.audit import record_audit_event

router = APIRouter(prefix="/auth")


class BootstrapStatusResponse(BaseModel):
    bootstrap_required: bool


class UserSummary(BaseModel):
    id: str
    username: str
    display_name: str | None
    email: str | None
    phone: str | None
    timezone: str
    is_admin: bool
    is_disabled: bool
    avatar_url: str | None


class SessionResponse(BaseModel):
    user: UserSummary


class AuthRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=128)
    remember_me: bool = False


class RegisterRequest(AuthRequest):
    registration_code: str = Field(min_length=8, max_length=128)


@dataclass(frozen=True)
class AuthResolution:
    session: AuthSession
    session_token: str | None = None
    remember_token: str | None = None


def utcnow() -> datetime:
    return datetime.now(tz=UTC)


def as_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def cookie_path(settings: Settings) -> str:
    return settings.normalized_app_base_path or "/"


def normalize_username(username: str) -> str:
    return username.strip()


def serialize_user(user: User, settings: Settings) -> UserSummary:
    avatar_url = None
    if user.profile_images:
        latest_image = user.profile_images[-1]
        avatar_url = f"{settings.public_base_url}/api/v1/users/{user.id}/avatar?v={latest_image.id}"
    return UserSummary(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        email=user.email,
        phone=user.phone,
        timezone=user.timezone,
        is_admin=user.is_admin,
        is_disabled=user.is_disabled,
        avatar_url=avatar_url,
    )


def set_session_cookie(response: Response, *, settings: Settings, raw_token: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=encode_signed_token(raw_token, settings.session_key or ""),
        max_age=settings.session_duration_minutes * 60,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path=cookie_path(settings),
    )


def set_remember_cookie(response: Response, *, settings: Settings, raw_token: str) -> None:
    response.set_cookie(
        key=settings.remember_cookie_name,
        value=encode_signed_token(raw_token, settings.session_key or ""),
        max_age=settings.remember_duration_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path=cookie_path(settings),
    )


def clear_session_cookie(response: Response, *, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path=cookie_path(settings),
    )


def clear_remember_cookie(response: Response, *, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.remember_cookie_name,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path=cookie_path(settings),
    )


def create_session(
    db: Session,
    *,
    user: User,
    settings: Settings,
    request: Request,
) -> tuple[str, AuthSession]:
    raw_token = generate_token()
    now = utcnow()
    auth_session = AuthSession(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        created_at=now,
        last_seen_at=now,
        expires_at=now + timedelta(minutes=settings.session_duration_minutes),
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    db.add(auth_session)
    return raw_token, auth_session


def create_auth_refresh_token(
    db: Session,
    *,
    user: User,
    settings: Settings,
    request: Request,
) -> tuple[str, AuthRefreshToken]:
    raw_token = generate_token()
    now = utcnow()
    refresh_token = AuthRefreshToken(
        token_hash=hash_token(raw_token),
        user_id=user.id,
        created_at=now,
        expires_at=now + timedelta(days=settings.remember_duration_days),
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    db.add(refresh_token)
    return raw_token, refresh_token


def revoke_remember_cookie_token(request: Request, db: Session, settings: Settings) -> None:
    cookie_value = request.cookies.get(settings.remember_cookie_name)
    if cookie_value is None:
        return
    raw_token = decode_signed_token(cookie_value, settings.session_key or "")
    if raw_token is None:
        return
    refresh_token = db.scalar(
        select(AuthRefreshToken).where(AuthRefreshToken.token_hash == hash_token(raw_token))
    )
    if refresh_token is None or refresh_token.revoked_at is not None:
        return
    refresh_token.revoked_at = utcnow()
    record_audit_event(
        db,
        event_type="auth.remember.revoke",
        message="Remember-me token revoked.",
        actor=refresh_token.user,
        details={"refresh_token_id": refresh_token.id},
    )


def apply_auth_cookies(
    response: Response,
    *,
    resolution: AuthResolution,
    settings: Settings,
) -> None:
    if resolution.session_token is not None:
        set_session_cookie(response, settings=settings, raw_token=resolution.session_token)
    if resolution.remember_token is not None:
        set_remember_cookie(response, settings=settings, raw_token=resolution.remember_token)


def read_session_from_cookie(request: Request, db: Session, settings: Settings) -> AuthSession | None:
    cookie_value = request.cookies.get(settings.session_cookie_name)
    if cookie_value is None:
        return None
    raw_token = decode_signed_token(cookie_value, settings.session_key or "")
    if raw_token is None:
        return None
    auth_session = db.scalar(select(AuthSession).where(AuthSession.token_hash == hash_token(raw_token)))
    now = utcnow()
    if (
        auth_session is None
        or auth_session.revoked_at is not None
        or as_aware_utc(auth_session.expires_at) <= now
    ):
        return None
    return auth_session


def refresh_session_from_remember_cookie(
    request: Request,
    db: Session,
    settings: Settings,
) -> AuthResolution | None:
    cookie_value = request.cookies.get(settings.remember_cookie_name)
    if cookie_value is None:
        return None
    raw_token = decode_signed_token(cookie_value, settings.session_key or "")
    if raw_token is None:
        return None
    refresh_token = db.scalar(
        select(AuthRefreshToken).where(AuthRefreshToken.token_hash == hash_token(raw_token))
    )
    now = utcnow()
    if (
        refresh_token is None
        or refresh_token.revoked_at is not None
        or as_aware_utc(refresh_token.expires_at) <= now
    ):
        return None
    if refresh_token.user.is_disabled:
        refresh_token.revoked_at = now
        db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is disabled.")

    refresh_token.revoked_at = now
    refresh_token.last_used_at = now
    raw_session_token, auth_session = create_session(
        db,
        user=refresh_token.user,
        settings=settings,
        request=request,
    )
    raw_remember_token, replacement = create_auth_refresh_token(
        db,
        user=refresh_token.user,
        settings=settings,
        request=request,
    )
    db.flush()
    refresh_token.replaced_by_token_id = replacement.id
    record_audit_event(
        db,
        event_type="auth.remember.refresh",
        message="Remember-me token refreshed auth session.",
        actor=refresh_token.user,
        details={
            "refresh_token_id": refresh_token.id,
            "replacement_refresh_token_id": replacement.id,
        },
    )
    db.commit()
    db.refresh(auth_session)
    return AuthResolution(
        session=auth_session,
        session_token=raw_session_token,
        remember_token=raw_remember_token,
    )


def resolve_authenticated_session(request: Request, db: Session, settings: Settings) -> AuthResolution:
    auth_session = read_session_from_cookie(request, db, settings)
    if auth_session is not None:
        if auth_session.user.is_disabled:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is disabled.")
        auth_session.last_seen_at = utcnow()
        db.commit()
        return AuthResolution(session=auth_session)

    refreshed_session = refresh_session_from_remember_cookie(request, db, settings)
    if refreshed_session is not None:
        return refreshed_session
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")


def get_authenticated_session(
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthSession:
    resolution = resolve_authenticated_session(request, db, settings)
    apply_auth_cookies(response, resolution=resolution, settings=settings)
    return resolution.session


def get_current_user(auth_session: Annotated[AuthSession, Depends(get_authenticated_session)]) -> User:
    return auth_session.user


def get_current_admin_user(user: Annotated[User, Depends(get_current_user)]) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required.")
    return user


@router.get("/bootstrap-status", response_model=BootstrapStatusResponse)
def bootstrap_status(db: Annotated[Session, Depends(get_db)]) -> BootstrapStatusResponse:
    return BootstrapStatusResponse(bootstrap_required=db.scalar(select(func.count(User.id))) == 0)


@router.post("/bootstrap", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def bootstrap(
    payload: AuthRequest,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SessionResponse:
    if db.scalar(select(func.count(User.id))) != 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bootstrap is already complete.")
    now = utcnow()
    user = User(
        username=normalize_username(payload.username),
        password_hash=hash_password(payload.password),
        timezone="America/Chicago",
        is_admin=True,
        created_at=now,
        updated_at=now,
        password_changed_at=now,
    )
    db.add(user)
    db.flush()
    raw_token, _auth_session = create_session(db, user=user, settings=settings, request=request)
    revoke_remember_cookie_token(request, db, settings)
    raw_remember_token = None
    if payload.remember_me:
        raw_remember_token, _remember_token = create_auth_refresh_token(
            db,
            user=user,
            settings=settings,
            request=request,
        )
    record_audit_event(
        db,
        event_type="auth.bootstrap",
        message="Bootstrap admin created.",
        actor=user,
        details={"username": user.username, "remember_me": payload.remember_me},
    )
    db.commit()
    db.refresh(user)
    set_session_cookie(response, settings=settings, raw_token=raw_token)
    if raw_remember_token is not None:
        set_remember_cookie(response, settings=settings, raw_token=raw_remember_token)
    else:
        clear_remember_cookie(response, settings=settings)
    return SessionResponse(user=serialize_user(user, settings))


@router.post("/login", response_model=SessionResponse)
def login(
    payload: AuthRequest,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SessionResponse:
    user = db.scalar(select(User).where(User.username == normalize_username(payload.username)))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password.")
    if user.is_disabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is disabled.")
    raw_token, _auth_session = create_session(db, user=user, settings=settings, request=request)
    revoke_remember_cookie_token(request, db, settings)
    raw_remember_token = None
    if payload.remember_me:
        raw_remember_token, _remember_token = create_auth_refresh_token(
            db,
            user=user,
            settings=settings,
            request=request,
        )
    record_audit_event(
        db,
        event_type="auth.login",
        message="User logged in.",
        actor=user,
        details={"username": user.username, "remember_me": payload.remember_me},
    )
    db.commit()
    db.refresh(user)
    set_session_cookie(response, settings=settings, raw_token=raw_token)
    if raw_remember_token is not None:
        set_remember_cookie(response, settings=settings, raw_token=raw_remember_token)
    else:
        clear_remember_cookie(response, settings=settings)
    return SessionResponse(user=serialize_user(user, settings))


@router.post("/register", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SessionResponse:
    username = normalize_username(payload.username)
    if db.scalar(select(User.id).where(User.username == username)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists.")
    code = db.scalar(
        select(RegistrationCode).where(RegistrationCode.code_hash == hash_token(payload.registration_code))
    )
    now = utcnow()
    if code is None or code.revoked_at is not None or as_aware_utc(code.expires_at) <= now:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Registration code is invalid.",
        )
    user = User(
        username=username,
        password_hash=hash_password(payload.password),
        timezone="America/Chicago",
        registration_code_id=code.id,
        created_at=now,
        updated_at=now,
        password_changed_at=now,
    )
    db.add(user)
    db.flush()
    raw_token, _auth_session = create_session(db, user=user, settings=settings, request=request)
    revoke_remember_cookie_token(request, db, settings)
    raw_remember_token = None
    if payload.remember_me:
        raw_remember_token, _remember_token = create_auth_refresh_token(
            db,
            user=user,
            settings=settings,
            request=request,
        )
    record_audit_event(
        db,
        event_type="auth.register",
        message="User registered.",
        actor=user,
        details={
            "username": user.username,
            "registration_code_id": code.id,
            "remember_me": payload.remember_me,
        },
    )
    db.commit()
    db.refresh(user)
    set_session_cookie(response, settings=settings, raw_token=raw_token)
    if raw_remember_token is not None:
        set_remember_cookie(response, settings=settings, raw_token=raw_remember_token)
    else:
        clear_remember_cookie(response, settings=settings)
    return SessionResponse(user=serialize_user(user, settings))


@router.get("/me", response_model=SessionResponse)
def me(
    user: Annotated[User, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SessionResponse:
    return SessionResponse(user=serialize_user(user, settings))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    cookie_value = request.cookies.get(settings.session_cookie_name)
    if cookie_value is not None:
        raw_token = decode_signed_token(cookie_value, settings.session_key or "")
        if raw_token is not None:
            auth_session = db.scalar(
                select(AuthSession).where(AuthSession.token_hash == hash_token(raw_token))
            )
            if auth_session is not None and auth_session.revoked_at is None:
                auth_session.revoked_at = utcnow()
                record_audit_event(
                    db,
                    event_type="auth.logout",
                    message="User logged out.",
                    actor=auth_session.user,
                    details={"session_id": auth_session.id},
                )
                db.commit()
    revoke_remember_cookie_token(request, db, settings)
    db.commit()
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_session_cookie(response, settings=settings)
    clear_remember_cookie(response, settings=settings)
    return response
