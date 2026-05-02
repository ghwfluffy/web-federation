from __future__ import annotations

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
from app.db import AuthSession, RegistrationCode, User, get_db

router = APIRouter(prefix="/auth")


class BootstrapStatusResponse(BaseModel):
    bootstrap_required: bool


class UserSummary(BaseModel):
    id: str
    username: str
    display_name: str | None
    timezone: str
    is_admin: bool
    is_disabled: bool
    avatar_url: str | None


class SessionResponse(BaseModel):
    user: UserSummary


class AuthRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=128)


class RegisterRequest(AuthRequest):
    registration_code: str = Field(min_length=8, max_length=128)


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


def clear_session_cookie(response: Response, *, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
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
) -> str:
    raw_token = generate_token()
    now = utcnow()
    db.add(
        AuthSession(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            created_at=now,
            last_seen_at=now,
            expires_at=now + timedelta(minutes=settings.session_duration_minutes),
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )
    )
    return raw_token


def get_authenticated_session(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthSession:
    cookie_value = request.cookies.get(settings.session_cookie_name)
    if cookie_value is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")
    raw_token = decode_signed_token(cookie_value, settings.session_key or "")
    if raw_token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")
    auth_session = db.scalar(select(AuthSession).where(AuthSession.token_hash == hash_token(raw_token)))
    now = utcnow()
    if (
        auth_session is None
        or auth_session.revoked_at is not None
        or as_aware_utc(auth_session.expires_at) <= now
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")
    if auth_session.user.is_disabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is disabled.")
    auth_session.last_seen_at = now
    db.commit()
    return auth_session


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
    raw_token = create_session(db, user=user, settings=settings, request=request)
    db.commit()
    db.refresh(user)
    set_session_cookie(response, settings=settings, raw_token=raw_token)
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
    raw_token = create_session(db, user=user, settings=settings, request=request)
    db.commit()
    db.refresh(user)
    set_session_cookie(response, settings=settings, raw_token=raw_token)
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
    raw_token = create_session(db, user=user, settings=settings, request=request)
    db.commit()
    db.refresh(user)
    set_session_cookie(response, settings=settings, raw_token=raw_token)
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
                db.commit()
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_session_cookie(response, settings=settings)
    return response
