# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""POST /v1/auth/{register,login,refresh,logout}, GET /v1/me, GET /v1/brand."""
from __future__ import annotations

import re
import secrets as _secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from wanxiang.api.auth_jwt import (
    decode_token,
    issue_access_token,
    issue_refresh_token,
)
from wanxiang.api.auth_user import require_user
from wanxiang.api.i18n import get_request_locale, normalize_locale, t
from wanxiang.api.users import (
    EMAIL_RE,
    PHONE_CN_RE,
    User,
    hash_password,
    validate_password,
    verify_password,
)
from wanxiang.api.workspaces import Workspace, WorkspaceMember


router = APIRouter()


class RegisterReq(BaseModel):
    email: str | None = None
    phone: str | None = None
    password: str = Field(min_length=1, max_length=128)
    display_name: str = Field(min_length=1, max_length=64)
    locale: str = "zh"


class LoginReq(BaseModel):
    identifier: str
    password: str


class RefreshReq(BaseModel):
    refresh_token: str


def _issue_tokens(user, settings):
    access = issue_access_token(
        user_id=user.user_id, secret=settings.jwt_secret,
        alg=settings.jwt_alg,
        ttl_minutes=settings.jwt_access_ttl_minutes)
    refresh, _jti = issue_refresh_token(
        user_id=user.user_id, secret=settings.jwt_secret,
        alg=settings.jwt_alg,
        ttl_days=settings.jwt_refresh_ttl_days)
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "Bearer",
    }


def _make_slug(name: str, ws_store) -> str:
    base = re.sub(r"[^a-z0-9-]", "-", name.lower())[:32]
    base = re.sub(r"-+", "-", base).strip("-") or "workspace"
    slug = base
    while ws_store.get_by_slug(slug):
        slug = f"{base}-{_secrets.token_hex(2)}"
    return slug


@router.post("/auth/register")
def register(req: RegisterReq, request: Request):
    locale = get_request_locale(request)
    if not (req.email or req.phone):
        raise HTTPException(
            400, t("auth.email_or_phone_required", locale=locale))
    if req.email and not EMAIL_RE.match(req.email):
        raise HTTPException(
            400, t("auth.invalid_phone_format", locale=locale))
    if req.phone and not PHONE_CN_RE.match(req.phone):
        raise HTTPException(
            400, t("auth.invalid_phone_format", locale=locale))
    pw_err = validate_password(req.password)
    if pw_err:
        raise HTTPException(400, t(pw_err, locale=locale))
    user_store = request.app.state.user_store
    if req.email and user_store.get_by_email(req.email):
        raise HTTPException(
            409, t("auth.email_already_registered", locale=locale))
    if req.phone and user_store.get_by_phone(req.phone):
        raise HTTPException(
            409, t("auth.phone_already_registered", locale=locale))
    user_locale = normalize_locale(req.locale) or "zh"
    user = User(user_id="auto", email=req.email, phone=req.phone,
                 password_hash=hash_password(req.password),
                 display_name=req.display_name,
                 locale=user_locale)
    user = user_store.create(user)
    # Auto-create personal workspace
    ws_store = request.app.state.workspace_store
    slug = _make_slug(req.display_name, ws_store)
    ws_name = (f"{req.display_name}'s Space" if locale == "en"
                else f"{req.display_name} 的工作区")
    ws = Workspace(workspace_id="auto", slug=slug, name=ws_name,
                    type="personal", owner_user_id=user.user_id,
                    locale=user.locale)
    ws = ws_store.create_workspace(ws)
    ws_store.add_member(WorkspaceMember(
        workspace_id=ws.workspace_id, user_id=user.user_id, role="owner"))
    tokens = _issue_tokens(user, request.app.state.settings)
    return {**tokens, "user": user.to_safe_dict(),
            "default_workspace": ws.to_dict()}


@router.post("/auth/login")
def login(req: LoginReq, request: Request):
    locale = get_request_locale(request)
    user_store = request.app.state.user_store
    user = None
    if EMAIL_RE.match(req.identifier):
        user = user_store.get_by_email(req.identifier)
    elif PHONE_CN_RE.match(req.identifier):
        user = user_store.get_by_phone(req.identifier)
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            401, t("auth.invalid_credentials", locale=locale))
    tokens = _issue_tokens(user, request.app.state.settings)
    workspaces = request.app.state.workspace_store.list_for_user(user.user_id)
    return {**tokens, "user": user.to_safe_dict(),
            "workspaces": [w.to_dict() for w in workspaces]}


@router.post("/auth/refresh")
def refresh(req: RefreshReq, request: Request):
    locale = get_request_locale(request)
    settings = request.app.state.settings
    claims = decode_token(req.refresh_token, secret=settings.jwt_secret,
                           alg=settings.jwt_alg, expected_type="refresh")
    if not claims:
        raise HTTPException(401, t("auth.invalid_token", locale=locale))
    user = request.app.state.user_store.get(claims["sub"])
    if not user:
        raise HTTPException(401, t("auth.user_not_found", locale=locale))
    return _issue_tokens(user, settings)


@router.post("/auth/logout")
def logout():
    """Stateless logout — frontend drops the token.

    A blacklist using ``jti`` will land in P2 (Redis-backed)."""
    return {"ok": True}


@router.get("/me")
def me(request: Request, user=Depends(require_user)):
    workspaces = request.app.state.workspace_store.list_for_user(user.user_id)
    return {
        "user": user.to_safe_dict(),
        "workspaces": [w.to_dict() for w in workspaces],
    }


@router.get("/brand")
def brand(request: Request):
    """Public brand config. No auth — frontend reads at boot."""
    s = request.app.state.settings
    return {
        "name": {"zh": s.brand_name_zh, "en": s.brand_name_en},
        "short": s.brand_short,
        "avatar": {"zh": s.brand_avatar_zh, "en": s.brand_avatar_en},
        "tagline": {"zh": s.brand_tagline_zh, "en": s.brand_tagline_en},
    }
