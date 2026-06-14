# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""GET/POST /v1/templates —— 场景模板列表 / 详情 / 实例化。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from wanxiang.api.auth import require_tenant
from wanxiang.api.tenancy import TenantInfo
from wanxiang.scenarios import (ScenarioTemplate, instantiate, list_templates,
                                  load_template)

router = APIRouter()


def _summary(t: ScenarioTemplate) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "description": t.description,
        "decision_kind": t.decision_kind.value,
        "variables": list(t.variables),
        "default_options": list(t.default_options) if t.default_options else None,
    }


def _full(t: ScenarioTemplate) -> dict:
    out = _summary(t)
    out["material_template"] = t.material_template
    out["question_template"] = t.question_template
    return out


class InstantiateRequest(BaseModel):
    values: dict[str, Any] = {}
    options: list[str] | None = None


@router.get("/templates")
def list_all(tenant: TenantInfo = Depends(require_tenant)) -> list[dict]:
    return [_summary(t) for t in list_templates()]


@router.get("/templates/{template_id}")
def get_one(template_id: str,
            tenant: TenantInfo = Depends(require_tenant)) -> dict:
    try:
        t = load_template(template_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404,
                            detail=f"template not found: {template_id}")
    return _full(t)


@router.post("/templates/{template_id}/instantiate")
def post_instantiate(
    template_id: str,
    body: InstantiateRequest,
    tenant: TenantInfo = Depends(require_tenant),
) -> dict:
    try:
        t = load_template(template_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404,
                            detail=f"template not found: {template_id}")
    try:
        return instantiate(t, body.values, options=body.options)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
