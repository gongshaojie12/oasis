# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""P3: Workspace-scoped API key management routes."""
from __future__ import annotations

import secrets
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from wanxiang.api.api_keys import ApiKey
from wanxiang.api.auth_user import require_user
from wanxiang.api.i18n import get_request_locale, t

router = APIRouter()


class CreateApiKeyReq(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    role: Literal["admin", "member"] = "member"
    rpm_limit: int = Field(default=60, ge=1, le=10_000)
    monthly_budget: int | None = None


def _preview(key: str) -> str:
    return (key[:6] + "...") if len(key) > 6 else "..."


@router.get("/workspaces/{slug}/api-keys")
def list_api_keys(slug: str, request: Request,
                    user=Depends(require_user)):
    locale = get_request_locale(request)
    ws = request.app.state.workspace_store.get_by_slug(slug)
    if not ws:
        raise HTTPException(
            404, t("workspace.not_found", locale=locale))
    from wanxiang.api.routes.workspaces import _require_admin_or_owner
    _require_admin_or_owner(request, ws.workspace_id, user.user_id, locale)
    keys = request.app.state.api_key_store.list_for_workspace(
        ws.workspace_id)
    return {"api_keys": [{
        "key_id": k.key_id,
        "name": k.name,
        "api_key_preview": _preview(k.api_key),
        "role": k.role,
        "rpm_limit": k.rpm_limit,
        "monthly_budget": k.monthly_budget,
        "created_at": k.created_at.isoformat(),
    } for k in keys]}


@router.post("/workspaces/{slug}/api-keys")
def create_api_key(slug: str, req: CreateApiKeyReq, request: Request,
                     user=Depends(require_user)):
    locale = get_request_locale(request)
    ws = request.app.state.workspace_store.get_by_slug(slug)
    if not ws:
        raise HTTPException(
            404, t("workspace.not_found", locale=locale))
    from wanxiang.api.routes.workspaces import _require_admin_or_owner
    _require_admin_or_owner(request, ws.workspace_id, user.user_id, locale)
    raw_key = "wxk-" + secrets.token_urlsafe(28)
    ak = ApiKey(
        key_id="auto", workspace_id=ws.workspace_id, api_key=raw_key,
        name=req.name, role=req.role, rpm_limit=req.rpm_limit,
        monthly_budget=req.monthly_budget,
        created_by_user_id=user.user_id,
    )
    ak = request.app.state.api_key_store.create(ak)
    return {
        "key_id": ak.key_id,
        "api_key": raw_key,
        "name": ak.name,
        "role": ak.role,
        "rpm_limit": ak.rpm_limit,
        "monthly_budget": ak.monthly_budget,
        "created_at": ak.created_at.isoformat(),
        "warning": "Save this key now; it will not be shown again.",
    }


@router.delete("/workspaces/{slug}/api-keys/{key_id}")
def revoke_api_key(slug: str, key_id: str, request: Request,
                     user=Depends(require_user)):
    locale = get_request_locale(request)
    ws = request.app.state.workspace_store.get_by_slug(slug)
    if not ws:
        raise HTTPException(
            404, t("workspace.not_found", locale=locale))
    from wanxiang.api.routes.workspaces import _require_admin_or_owner
    _require_admin_or_owner(request, ws.workspace_id, user.user_id, locale)
    ok = request.app.state.api_key_store.revoke(key_id)
    if not ok:
        raise HTTPException(
            404, t("workspace.api_key_not_found", locale=locale))
    return {"ok": True}
