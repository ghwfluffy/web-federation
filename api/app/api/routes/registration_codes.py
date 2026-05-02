from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes.auth import get_current_admin_user, utcnow
from app.core.security import generate_token, hash_token
from app.db import RegistrationCode, User, get_db

router = APIRouter(prefix="/registration-codes")


class RegistrationCodeSummary(BaseModel):
    id: str
    code: str | None = None
    description: str | None
    expires_at: str
    revoked_at: str | None
    created_at: str
    created_by_user_id: str | None


class RegistrationCodeListResponse(BaseModel):
    registration_codes: list[RegistrationCodeSummary]


class CreateRegistrationCodeRequest(BaseModel):
    description: str | None = Field(default=None, max_length=200)
    expires_at: datetime


class UpdateRegistrationCodeRequest(BaseModel):
    description: str | None = Field(default=None, max_length=200)
    expires_at: datetime


def serialize_registration_code(
    code: RegistrationCode,
    *,
    raw_code: str | None = None,
) -> RegistrationCodeSummary:
    return RegistrationCodeSummary(
        id=code.id,
        code=raw_code,
        description=code.description,
        expires_at=code.expires_at.isoformat(),
        revoked_at=code.revoked_at.isoformat() if code.revoked_at else None,
        created_at=code.created_at.isoformat(),
        created_by_user_id=code.created_by_user_id,
    )


@router.get("", response_model=RegistrationCodeListResponse)
def list_registration_codes(
    _admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> RegistrationCodeListResponse:
    rows = list(db.scalars(select(RegistrationCode).order_by(RegistrationCode.created_at.desc())))
    return RegistrationCodeListResponse(registration_codes=[serialize_registration_code(row) for row in rows])


@router.post("", response_model=RegistrationCodeSummary, status_code=status.HTTP_201_CREATED)
def create_registration_code(
    payload: CreateRegistrationCodeRequest,
    admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> RegistrationCodeSummary:
    raw_code = generate_token(24)
    now = utcnow()
    code = RegistrationCode(
        code_hash=hash_token(raw_code),
        description=payload.description,
        expires_at=payload.expires_at,
        created_by_user_id=admin.id,
        created_at=now,
        updated_at=now,
    )
    db.add(code)
    db.commit()
    db.refresh(code)
    return serialize_registration_code(code, raw_code=raw_code)


@router.patch("/{code_id}", response_model=RegistrationCodeSummary)
def update_registration_code(
    code_id: str,
    payload: UpdateRegistrationCodeRequest,
    _admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> RegistrationCodeSummary:
    code = db.get(RegistrationCode, code_id)
    if code is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration code not found.")
    code.description = payload.description
    code.expires_at = payload.expires_at
    code.updated_at = utcnow()
    db.commit()
    db.refresh(code)
    return serialize_registration_code(code)


@router.post("/{code_id}/revoke", response_model=RegistrationCodeSummary)
def revoke_registration_code(
    code_id: str,
    _admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> RegistrationCodeSummary:
    code = db.get(RegistrationCode, code_id)
    if code is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration code not found.")
    code.revoked_at = utcnow()
    code.updated_at = utcnow()
    db.commit()
    db.refresh(code)
    return serialize_registration_code(code)


@router.delete("/{code_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_registration_code(
    code_id: str,
    _admin: Annotated[User, Depends(get_current_admin_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    code = db.get(RegistrationCode, code_id)
    if code is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration code not found.")
    db.delete(code)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
