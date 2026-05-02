from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.routes.auth import get_current_admin_user, get_current_user, serialize_user, utcnow
from app.core.config import Settings, get_settings
from app.core.security import hash_password, verify_password
from app.db import AuthSession, User, UserProfileImage, get_db
from app.services.audit import record_audit_event
from app.services.images import ImageValidationError, render_safe_avatar_png

router = APIRouter(prefix="/users")


class UserListResponse(BaseModel):
    users: list[dict[str, object]]


class UpdateProfileRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=100)
    timezone: str = Field(default="America/Chicago", max_length=100)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class AdminCreateUserRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=100)
    timezone: str = Field(default="America/Chicago", max_length=100)
    is_admin: bool = False
    is_disabled: bool = False


class AdminUpdateUserRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=100)
    timezone: str = Field(default="America/Chicago", max_length=100)
    is_admin: bool = False
    is_disabled: bool = False


class AdminResetPasswordRequest(BaseModel):
    password: str = Field(min_length=8, max_length=128)


def admin_user_payload(user: User, settings: Settings) -> dict[str, object]:
    return serialize_user(user, settings).model_dump()


def admin_count(db: Session) -> int:
    return db.scalar(select(func.count(User.id)).where(User.is_admin.is_(True))) or 0


@router.get("/me")
def read_current_profile(
    user: Annotated[User, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, object]:
    return admin_user_payload(user, settings)


@router.patch("/me")
def update_current_profile(
    payload: UpdateProfileRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, object]:
    user.display_name = payload.display_name
    user.timezone = payload.timezone
    user.updated_at = utcnow()
    record_audit_event(
        db,
        event_type="user.profile.update",
        message="User profile updated.",
        actor=user,
        details={"user_id": user.id},
    )
    db.commit()
    db.refresh(user)
    return admin_user_payload(user, settings)


@router.post("/me/change-password")
def change_password(
    payload: ChangePasswordRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, object]:
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Current password is invalid.",
        )
    user.password_hash = hash_password(payload.new_password)
    user.password_changed_at = utcnow()
    user.updated_at = utcnow()
    db.query(AuthSession).filter(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None)).update(
        {"revoked_at": utcnow()},
        synchronize_session=False,
    )
    record_audit_event(
        db,
        event_type="user.password.change",
        message="User password changed.",
        actor=user,
        details={"user_id": user.id},
    )
    db.commit()
    db.refresh(user)
    return admin_user_payload(user, settings)


@router.post("/me/avatar")
async def upload_current_avatar(
    avatar: Annotated[UploadFile, File(...)],
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, object]:
    try:
        png_bytes, width, height, sha256 = render_safe_avatar_png(await avatar.read())
    except ImageValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    image = UserProfileImage(user_id=user.id, png_bytes=png_bytes, width=width, height=height, sha256=sha256)
    db.add(image)
    user.updated_at = utcnow()
    record_audit_event(
        db,
        event_type="user.avatar.change",
        message="User avatar changed.",
        actor=user,
        details={"user_id": user.id, "image_id": image.id},
    )
    db.commit()
    db.refresh(user)
    return admin_user_payload(user, settings)


@router.get("/{user_id}/avatar")
def read_user_avatar(user_id: str, db: Annotated[Session, Depends(get_db)]) -> Response:
    image = db.scalar(
        select(UserProfileImage)
        .where(UserProfileImage.user_id == user_id)
        .order_by(UserProfileImage.created_at.desc())
    )
    if image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avatar not found.")
    return Response(content=image.png_bytes, media_type="image/png")


@router.get("", response_model=UserListResponse)
def list_users(
    _admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> UserListResponse:
    users = list(db.scalars(select(User).order_by(User.created_at.asc())))
    return UserListResponse(users=[admin_user_payload(user, settings) for user in users])


@router.post("", status_code=status.HTTP_201_CREATED)
def admin_create_user(
    payload: AdminCreateUserRequest,
    _admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, object]:
    if db.scalar(select(User.id).where(User.username == payload.username.strip())) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists.")
    now = utcnow()
    user = User(
        username=payload.username.strip(),
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
        timezone=payload.timezone,
        is_admin=payload.is_admin,
        is_disabled=payload.is_disabled,
        created_at=now,
        updated_at=now,
        password_changed_at=now,
    )
    db.add(user)
    record_audit_event(
        db,
        event_type="admin.user.create",
        message="Admin created user.",
        actor=_admin,
        details={"target_username": user.username},
    )
    db.commit()
    db.refresh(user)
    return admin_user_payload(user, settings)


@router.patch("/{user_id}")
def admin_update_user(
    user_id: str,
    payload: AdminUpdateUserRequest,
    _admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, object]:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if (
        user.is_admin
        and not payload.is_admin
        and admin_count(db) <= 1
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Cannot remove the last admin.",
        )
    user.display_name = payload.display_name
    user.timezone = payload.timezone
    user.is_admin = payload.is_admin
    user.is_disabled = payload.is_disabled
    user.updated_at = utcnow()
    record_audit_event(
        db,
        event_type="admin.user.update",
        message="Admin updated user.",
        actor=_admin,
        details={"target_user_id": user.id},
    )
    db.commit()
    db.refresh(user)
    return admin_user_payload(user, settings)


@router.post("/{user_id}/reset-password")
def admin_reset_password(
    user_id: str,
    payload: AdminResetPasswordRequest,
    _admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, object]:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    user.password_hash = hash_password(payload.password)
    user.password_changed_at = utcnow()
    user.updated_at = utcnow()
    db.query(AuthSession).filter(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None)).update(
        {"revoked_at": utcnow()},
        synchronize_session=False,
    )
    record_audit_event(
        db,
        event_type="admin.user.reset_password",
        message="Admin reset user password.",
        actor=_admin,
        details={"target_user_id": user.id},
    )
    db.commit()
    db.refresh(user)
    return admin_user_payload(user, settings)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_user(
    user_id: str,
    admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Use profile deletion later.",
        )
    if user.is_admin and admin_count(db) <= 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Cannot delete the last admin.",
        )
    record_audit_event(
        db,
        event_type="admin.user.delete",
        message="Admin deleted user.",
        actor=admin,
        details={"target_user_id": user.id, "target_username": user.username},
    )
    db.delete(user)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
