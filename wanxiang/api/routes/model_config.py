# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""模型配置路由:provider 预设 + 每工作区 provider/key 读写。

- GET /v1/model-presets                      登录可读
- GET /v1/workspaces/{slug}/model-config     member 可读(key 脱敏)
- PUT /v1/workspaces/{slug}/model-config     owner/admin 可写
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from wanxiang.api.auth_user import require_user
from wanxiang.api.i18n import get_request_locale, t
from wanxiang.api.model_config import ModelConfigRecord
from wanxiang.api.model_presets import MODEL_PRESETS, get_preset, mask_key

router = APIRouter()


class ModelConfigPut(BaseModel):
    provider: str
    api_key: str | None = None
    base_url: str | None = None
    model_name: str | None = None


def _resolve_member(slug: str, request: Request, user, locale):
    ws = request.app.state.workspace_store.get_by_slug(slug)
    if not ws:
        raise HTTPException(status_code=404, detail="workspace not found")
    m = request.app.state.workspace_store.get_member(
        ws.workspace_id, user.user_id)
    if not m:
        raise HTTPException(
            status_code=403, detail=t("workspace.not_a_member", locale=locale))
    return ws, m


def _serialize(rec: ModelConfigRecord | None) -> dict:
    if rec is None:
        return {"provider": "stub", "api_key_masked": None,
                "base_url": None, "model_name": None, "has_key": False,
                "updated_at": None, "updated_by": None}
    return {
        "provider": rec.provider,
        "api_key_masked": mask_key(rec.api_key),
        "base_url": rec.base_url,
        "model_name": rec.model_name,
        "has_key": bool(rec.api_key),
        "updated_at": rec.updated_at.isoformat() if rec.updated_at else None,
        "updated_by": rec.updated_by_user_id,
    }


@router.get("/model-presets")
def list_presets(request: Request, user=Depends(require_user)):
    return {"presets": MODEL_PRESETS}


@router.get("/workspaces/{slug}/model-config")
def get_model_config(slug: str, request: Request,
                     user=Depends(require_user)):
    locale = get_request_locale(request)
    ws, _ = _resolve_member(slug, request, user, locale)
    rec = request.app.state.model_config_store.get(ws.workspace_id)
    return _serialize(rec)


@router.put("/workspaces/{slug}/model-config")
def put_model_config(slug: str, body: ModelConfigPut, request: Request,
                     user=Depends(require_user)):
    locale = get_request_locale(request)
    ws, member = _resolve_member(slug, request, user, locale)
    if member.role not in ("owner", "admin"):
        raise HTTPException(
            status_code=403, detail=t("workspace.requires_admin",
                                      locale=locale))

    preset = get_preset(body.provider)
    if preset is None:
        raise HTTPException(status_code=400,
                            detail=f"unknown provider: {body.provider}")

    store = request.app.state.model_config_store
    existing = store.get(ws.workspace_id)
    # key 留空 = 不改旧 key
    api_key = body.api_key if body.api_key else (
        existing.api_key if existing else None)

    if preset["needs_key"] and not api_key:
        raise HTTPException(
            status_code=400,
            detail=t("model_config.key_required", locale=locale))
    base_url = body.base_url or (preset["base_url"])
    if preset["allow_custom_base_url"] and not body.base_url:
        raise HTTPException(
            status_code=400,
            detail=t("model_config.base_url_required", locale=locale))

    rec = ModelConfigRecord(
        workspace_id=ws.workspace_id,
        provider=body.provider,
        api_key=api_key,
        base_url=base_url,
        model_name=body.model_name,
        updated_at=datetime.now(timezone.utc),
        updated_by_user_id=user.user_id,
    )
    store.upsert(rec)
    return _serialize(rec)
