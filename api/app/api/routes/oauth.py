from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Mapping
from datetime import timedelta
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Header, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes.auth import as_aware_utc, get_current_user, serialize_user, utcnow
from app.core.config import Settings, get_settings
from app.core.security import generate_token, hash_token, sign_value
from app.db import OAuthAuthorizationCode, OAuthClient, OAuthRefreshToken, User, get_db
from app.services.audit import record_audit_event

metadata_router = APIRouter()
router = APIRouter(prefix="/oauth")
ACCESS_TOKEN_SECONDS = 900
AUTHORIZATION_CODE_SECONDS = 300
REFRESH_TOKEN_DAYS = 30


class OpenIdConfiguration(BaseModel):
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    userinfo_endpoint: str
    revocation_endpoint: str
    jwks_uri: str
    response_types_supported: list[str]
    grant_types_supported: list[str]
    code_challenge_methods_supported: list[str]
    scopes_supported: list[str]
    subject_types_supported: list[str]
    id_token_signing_alg_values_supported: list[str]


def base64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def json_base64url(payload: Mapping[str, object]) -> str:
    return base64url(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))


def sign_jwt(payload: dict[str, object], settings: Settings) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    signing_input = f"{json_base64url(header)}.{json_base64url(payload)}"
    signature = sign_value(signing_input, settings.session_key or "")
    return f"{signing_input}.{base64url(bytes.fromhex(signature))}"


def decode_jwt(token: str, settings: Settings) -> dict[str, object] | None:
    try:
        header_raw, payload_raw, signature_raw = token.split(".")
        signing_input = f"{header_raw}.{payload_raw}"
        expected = base64url(bytes.fromhex(sign_value(signing_input, settings.session_key or "")))
        if signature_raw != expected:
            return None
        padded = payload_raw + "=" * (-len(payload_raw) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
    except (ValueError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    exp = payload.get("exp")
    if not isinstance(exp, int) or exp <= int(utcnow().timestamp()):
        return None
    return payload


def pkce_challenge(verifier: str) -> str:
    return base64url(hashlib.sha256(verifier.encode("ascii")).digest())


def get_client(db: Session, client_id: str) -> OAuthClient:
    client = db.scalar(select(OAuthClient).where(OAuthClient.client_id == client_id))
    if client is None or not client.is_enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth client.")
    return client


def require_redirect_uri(client: OAuthClient, redirect_uri: str) -> None:
    if redirect_uri not in client.redirect_uris:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid redirect URI.")


def bearer_payload(authorization: str | None, settings: Settings) -> dict[str, object]:
    if authorization is None or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token.")
    payload = decode_jwt(authorization[7:].strip(), settings)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bearer token.")
    return payload


def token_response(
    *,
    db: Session,
    user: User,
    client: OAuthClient,
    scope: str,
    settings: Settings,
) -> dict[str, object]:
    now = utcnow()
    access_payload = {
        "iss": settings.public_base_url,
        "sub": user.id,
        "aud": client.client_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ACCESS_TOKEN_SECONDS)).timestamp()),
        "scope": scope,
        "preferred_username": user.username,
        "name": user.display_name or user.username,
    }
    refresh_token = generate_token()
    db.add(
        OAuthRefreshToken(
            token_hash=hash_token(refresh_token),
            user_id=user.id,
            client_id=client.id,
            scope=scope,
            created_at=now,
            expires_at=now + timedelta(days=REFRESH_TOKEN_DAYS),
        )
    )
    record_audit_event(
        db,
        event_type="oauth.token.issue",
        message="OAuth tokens issued.",
        actor=user,
        details={"client_id": client.client_id, "scope": scope},
    )
    db.commit()
    return {
        "access_token": sign_jwt(access_payload, settings),
        "token_type": "Bearer",
        "expires_in": ACCESS_TOKEN_SECONDS,
        "refresh_token": refresh_token,
        "scope": scope,
    }


@metadata_router.get("/.well-known/openid-configuration", response_model=OpenIdConfiguration)
def openid_configuration(settings: Annotated[Settings, Depends(get_settings)]) -> OpenIdConfiguration:
    base_url = settings.public_base_url
    return OpenIdConfiguration(
        issuer=base_url,
        authorization_endpoint=f"{base_url}/oauth/authorize",
        token_endpoint=f"{base_url}/oauth/token",
        userinfo_endpoint=f"{base_url}/oauth/userinfo",
        revocation_endpoint=f"{base_url}/oauth/revoke",
        jwks_uri=f"{base_url}/oauth/jwks.json",
        response_types_supported=["code"],
        grant_types_supported=["authorization_code", "refresh_token"],
        code_challenge_methods_supported=["S256"],
        scopes_supported=["openid", "profile"],
        subject_types_supported=["public"],
        id_token_signing_alg_values_supported=["HS256"],
    )


@router.get("/authorize")
def authorize(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    response_type: str = Query(),
    client_id: str = Query(),
    redirect_uri: str = Query(),
    scope: str = Query(default="openid profile"),
    state: str | None = Query(default=None),
    code_challenge: str = Query(),
    code_challenge_method: str = Query(),
) -> RedirectResponse:
    if response_type != "code":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported response type.")
    if code_challenge_method != "S256":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PKCE S256 is required.")
    client = get_client(db, client_id)
    require_redirect_uri(client, redirect_uri)
    raw_code = generate_token()
    now = utcnow()
    db.add(
        OAuthAuthorizationCode(
            code_hash=hash_token(raw_code),
            user_id=current_user.id,
            client_id=client.id,
            redirect_uri=redirect_uri,
            scope=scope,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            created_at=now,
            expires_at=now + timedelta(seconds=AUTHORIZATION_CODE_SECONDS),
        )
    )
    record_audit_event(
        db,
        event_type="oauth.grant",
        message="OAuth authorization code granted.",
        actor=current_user,
        details={"client_id": client.client_id, "redirect_uri": redirect_uri, "scope": scope},
    )
    db.commit()
    query = {"code": raw_code}
    if state is not None:
        query["state"] = state
    return RedirectResponse(f"{redirect_uri}?{urlencode(query)}", status_code=status.HTTP_302_FOUND)


@router.post("/token")
def token(
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    grant_type: Annotated[str, Form()],
    client_id: Annotated[str, Form()],
    code: Annotated[str | None, Form()] = None,
    redirect_uri: Annotated[str | None, Form()] = None,
    code_verifier: Annotated[str | None, Form()] = None,
    refresh_token: Annotated[str | None, Form()] = None,
) -> dict[str, object]:
    client = get_client(db, client_id)
    now = utcnow()
    if grant_type == "authorization_code":
        if code is None or redirect_uri is None or code_verifier is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing authorization-code fields.",
            )
        auth_code = db.scalar(
            select(OAuthAuthorizationCode).where(OAuthAuthorizationCode.code_hash == hash_token(code))
        )
        if (
            auth_code is None
            or auth_code.client_id != client.id
            or auth_code.redirect_uri != redirect_uri
            or auth_code.consumed_at is not None
            or as_aware_utc(auth_code.expires_at) <= now
            or auth_code.code_challenge != pkce_challenge(code_verifier)
        ):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid authorization code.")
        auth_code.consumed_at = now
        user = db.get(User, auth_code.user_id)
        if user is None or user.is_disabled:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user.")
        return token_response(db=db, user=user, client=client, scope=auth_code.scope, settings=settings)
    if grant_type == "refresh_token":
        if refresh_token is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing refresh token.")
        token_record = db.scalar(
            select(OAuthRefreshToken).where(OAuthRefreshToken.token_hash == hash_token(refresh_token))
        )
        if (
            token_record is None
            or token_record.client_id != client.id
            or token_record.revoked_at is not None
            or as_aware_utc(token_record.expires_at) <= now
        ):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid refresh token.")
        user = db.get(User, token_record.user_id)
        if user is None or user.is_disabled:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user.")
        token_record.revoked_at = now
        record_audit_event(
            db,
            event_type="oauth.refresh.use",
            message="OAuth refresh token used.",
            actor=user,
            details={"client_id": client.client_id, "refresh_token_id": token_record.id},
        )
        response = token_response(
            db=db,
            user=user,
            client=client,
            scope=token_record.scope,
            settings=settings,
        )
        replacement = db.scalar(
            select(OAuthRefreshToken).where(
                OAuthRefreshToken.token_hash == hash_token(str(response["refresh_token"]))
            )
        )
        token_record.replaced_by_token_id = replacement.id if replacement is not None else None
        db.commit()
        return response
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported grant type.")


@router.get("/userinfo")
def userinfo(
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, object]:
    payload = bearer_payload(authorization, settings)
    user = db.get(User, payload.get("sub"))
    if user is None or user.is_disabled:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bearer token.")
    summary = serialize_user(user, settings)
    return {
        "sub": user.id,
        "preferred_username": user.username,
        "name": summary.display_name or user.username,
        "picture": summary.avatar_url,
        "updated_at": int(user.updated_at.timestamp()),
        "is_admin": user.is_admin,
    }


@router.post("/revoke", status_code=status.HTTP_204_NO_CONTENT)
def revoke(
    db: Annotated[Session, Depends(get_db)],
    token_value: Annotated[str, Form(alias="token")],
) -> None:
    token_record = db.scalar(
        select(OAuthRefreshToken).where(OAuthRefreshToken.token_hash == hash_token(token_value))
    )
    if token_record is not None and token_record.revoked_at is None:
        token_record.revoked_at = utcnow()
        record_audit_event(
            db,
            event_type="oauth.token.revoke",
            message="OAuth refresh token revoked.",
            details={"refresh_token_id": token_record.id, "client_id": token_record.client_id},
        )
        db.commit()


@router.get("/jwks.json")
def jwks(settings: Annotated[Settings, Depends(get_settings)]) -> dict[str, object]:
    key_material = hashlib.sha256((settings.session_key or "").encode("utf-8")).digest()
    return {"keys": [{"kty": "oct", "kid": "default", "alg": "HS256", "k": base64url(key_material)}]}
