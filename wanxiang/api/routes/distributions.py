# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""M1 人群画像库路由。

- GET    /v1/distributions                登录可读:列 enabled 画像(摘要)
- GET    /v1/distributions/{id}            登录可读:画像详情(含 content)
- POST   /v1/admin/distributions          超管:上传新画像(yaml/json 全文)
- PUT    /v1/admin/distributions/{id}     超管:改 name/描述/content/启用
- DELETE /v1/admin/distributions/{id}     超管:删除(builtin 禁删,仅可禁用)
- POST   /v1/admin/distributions/{id}/duplicate  超管:复制为新版编辑
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

import yaml
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from wanxiang.api.auth_user import require_super_admin, require_user
from wanxiang.api.distributions import (DistributionRecord, count_traits,
                                        slugify)
from wanxiang.datasources.distribution import validate_distribution
from wanxiang.personas.data_sources import UploadSource
from wanxiang.personas.ingest_compliance import (apply_input_dp, scan_pii,
                                                 synthetic_fill)

router = APIRouter()

_MAX_CONTENT_BYTES = 5 * 1024 * 1024  # 5MB 上限,防滥用


class UploadDistReq(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str = ""
    fmt: str = Field("json", pattern="^(yaml|json)$")
    content: str = Field(min_length=1)
    # 合规可选开关
    dp_epsilon: float | None = None       # 设了就给权重加 DP 噪声
    synthetic_fill: bool = False          # 缺 personality/media 时合成补缺


class UpdateDistReq(BaseModel):
    name: str | None = None
    description: str | None = None
    enabled: bool | None = None
    fmt: str | None = Field(None, pattern="^(yaml|json)$")
    content: str | None = None


def _parse_content(fmt: str, content: str) -> dict:
    if len(content.encode("utf-8")) > _MAX_CONTENT_BYTES:
        raise HTTPException(413, "画像内容超过 5MB 上限")
    try:
        if fmt == "json":
            return json.loads(content)
        return yaml.safe_load(content) or {}
    except (yaml.YAMLError, json.JSONDecodeError, ValueError) as e:
        raise HTTPException(400, f"内容解析失败({fmt}): {e}")


def _ingest(req_name: str, raw: dict, *, dp_epsilon: float | None,
            do_synthetic: bool) -> tuple[dict, list[str]]:
    """校验 → 多源接入(UploadSource)→ 可选合规 → 返回(规范化 content, 告警)。"""
    ok, errors = validate_distribution(raw)
    if not ok:
        raise HTTPException(status_code=400,
                            detail={"message": "画像校验失败",
                                    "errors": errors[:20]})
    profile = UploadSource(raw, req_name).load()
    warnings = scan_pii(profile)
    if do_synthetic:
        profile = synthetic_fill(profile)
    if dp_epsilon is not None:
        if dp_epsilon <= 0:
            raise HTTPException(400, "dp_epsilon 必须 > 0")
        profile = apply_input_dp(profile, epsilon=dp_epsilon)
    return profile.content, warnings + profile.notes


# ---- 读(登录可读)----

@router.get("/distributions")
def list_distributions(request: Request, user=Depends(require_user)):
    store = request.app.state.distribution_store
    recs = store.list_all(enabled_only=True)
    return {"distributions": [r.to_summary() for r in recs]}


@router.get("/distributions/{distribution_id}")
def get_distribution(distribution_id: str, request: Request,
                     user=Depends(require_user)):
    store = request.app.state.distribution_store
    rec = store.get(distribution_id) or store.get_by_slug(distribution_id)
    if not rec:
        raise HTTPException(404, "画像不存在")
    return rec.to_detail()


# ---- 写(超管)----

def _gen_id() -> str:
    import uuid
    return "dist_" + uuid.uuid4().hex[:16]


def _unique_slug(store, base: str) -> str:
    slug = base
    i = 2
    while store.get_by_slug(slug) is not None:
        slug = f"{base}-{i}"
        i += 1
    return slug


@router.post("/admin/distributions", status_code=201)
def create_distribution(req: UploadDistReq, request: Request,
                        user=Depends(require_super_admin)):
    store = request.app.state.distribution_store
    raw = _parse_content(req.fmt, req.content)
    content, warnings = _ingest(req.name, raw, dp_epsilon=req.dp_epsilon,
                                do_synthetic=req.synthetic_fill)
    now = datetime.now(timezone.utc)
    rec = DistributionRecord(
        distribution_id=_gen_id(),
        slug=_unique_slug(store, slugify(req.name)),
        name_zh=req.name, name_en=req.name, description=req.description,
        source_type="upload", content=content,
        trait_counts=count_traits(content),
        enabled=True, builtin=False,
        created_at=now, updated_at=now, created_by_user_id=user.user_id)
    store.upsert(rec)
    return {**rec.to_summary(), "warnings": warnings}


@router.put("/admin/distributions/{distribution_id}")
def update_distribution(distribution_id: str, req: UpdateDistReq,
                        request: Request, user=Depends(require_super_admin)):
    store = request.app.state.distribution_store
    rec = store.get(distribution_id)
    if not rec:
        raise HTTPException(404, "画像不存在")
    warnings: list[str] = []
    if req.content is not None:
        fmt = req.fmt or "json"
        raw = _parse_content(fmt, req.content)
        rec.content, warnings = _ingest(req.name or rec.name_zh, raw,
                                        dp_epsilon=None, do_synthetic=False)
        rec.trait_counts = count_traits(rec.content)
    if req.name is not None:
        rec.name_zh = req.name
        rec.name_en = req.name
    if req.description is not None:
        rec.description = req.description
    if req.enabled is not None:
        rec.enabled = req.enabled
    rec.updated_at = datetime.now(timezone.utc)
    store.upsert(rec)
    return {**rec.to_summary(), "warnings": warnings}


@router.delete("/admin/distributions/{distribution_id}")
def delete_distribution(distribution_id: str, request: Request,
                        user=Depends(require_super_admin)):
    store = request.app.state.distribution_store
    rec = store.get(distribution_id)
    if not rec:
        raise HTTPException(404, "画像不存在")
    if rec.builtin:
        # 内置画像禁删,只能禁用,避免破坏 seed 基线
        raise HTTPException(400, "内置画像不可删除,可改为禁用")
    store.delete(distribution_id)
    return {"deleted": distribution_id}


@router.post("/admin/distributions/{distribution_id}/duplicate",
             status_code=201)
def duplicate_distribution(distribution_id: str, request: Request,
                           user=Depends(require_super_admin)):
    store = request.app.state.distribution_store
    src = store.get(distribution_id)
    if not src:
        raise HTTPException(404, "画像不存在")
    now = datetime.now(timezone.utc)
    name = f"{src.name_zh} (副本)"
    rec = DistributionRecord(
        distribution_id=_gen_id(),
        slug=_unique_slug(store, slugify(name)),
        name_zh=name, name_en=name, description=src.description,
        source_type="upload", content=src.content,
        trait_counts=dict(src.trait_counts),
        enabled=True, builtin=False,
        created_at=now, updated_at=now, created_by_user_id=user.user_id)
    store.upsert(rec)
    return rec.to_summary()
