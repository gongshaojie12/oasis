# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""require_user / require_workspace FastAPI dependencies (P1)."""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request

from wanxiang.api.auth_jwt import decode_token
from wanxiang.api.i18n import get_request_locale, t


def get_bearer_token(request: Request) -> str | None:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip() or None
    return None


def require_user(request: Request):
    """FastAPI dep: requires valid Bearer JWT, returns User."""
    locale = get_request_locale(request)
    token = get_bearer_token(request)
    if not token:
        raise HTTPException(
            status_code=401,
            detail=t("auth.missing_token", locale=locale))
    settings = request.app.state.settings
    claims = decode_token(token, secret=settings.jwt_secret,
                           alg=settings.jwt_alg, expected_type="access")
    if not claims:
        raise HTTPException(
            status_code=401,
            detail=t("auth.invalid_token", locale=locale))
    user = request.app.state.user_store.get(claims["sub"])
    if not user:
        raise HTTPException(
            status_code=401,
            detail=t("auth.user_not_found", locale=locale))
    return user


def require_super_admin(user=Depends(require_user)):
    if not user.is_super_admin:
        raise HTTPException(status_code=403, detail="super-admin required")
    return user


def resolve_workspace(slug: str, request: Request,
                       user=Depends(require_user)):
    """For ``/w/{slug}/...`` routes. Verifies user is a member."""
    ws = request.app.state.workspace_store.get_by_slug(slug)
    if not ws:
        raise HTTPException(status_code=404, detail="workspace not found")
    member = request.app.state.workspace_store.get_member(
        ws.workspace_id, user.user_id)
    if not member:
        raise HTTPException(
            status_code=403, detail="not a member of this workspace")
    return ws


__all__ = ["require_user", "require_super_admin", "resolve_workspace",
           "get_bearer_token"]
