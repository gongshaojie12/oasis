# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""GET/POST /v1/templates —— 场景模板列表 / 详情 / 实例化。

P5: 所有端点响应都基于请求 locale（zh / en）选择对应语言的字段。
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from wanxiang.api.auth import require_tenant
from wanxiang.api.i18n import get_request_locale, t
from wanxiang.api.tenancy import TenantInfo
from wanxiang.scenarios import (ScenarioTemplate, instantiate, list_templates,
                                  load_template)

router = APIRouter()


def _pick_bilingual(value: Any, locale: str) -> Any:
    """If value is a {"zh","en"} dict, pick locale; otherwise return as-is."""
    if isinstance(value, dict) and "zh" in value and "en" in value:
        return value.get(locale) or value.get("zh") or ""
    return value


def _localized_variable(v: dict, locale: str) -> dict:
    """Render a variable dict for response: name as plain string,
    label/_label resolved to locale."""
    out: dict[str, Any] = {}
    for k, val in v.items():
        if k == "_label" and isinstance(val, dict):
            # Translate the human-facing variable label.
            out["label"] = val.get(locale) or val.get("zh") or ""
        elif k == "label" and isinstance(val, dict):
            out["label"] = val.get(locale) or val.get("zh") or ""
        else:
            out[k] = val
    return out


def _localized_default_options(opts: Any, locale: str) -> list[str] | None:
    if opts is None:
        return None
    if isinstance(opts, dict):
        return list(opts.get(locale) or opts.get("zh") or [])
    if isinstance(opts, list):
        return list(opts)
    return None


def _summary(tpl: ScenarioTemplate, locale: str) -> dict:
    return {
        "id": tpl.id,
        "name": _pick_bilingual(tpl.name, locale),
        "description": _pick_bilingual(tpl.description, locale),
        "decision_kind": tpl.decision_kind.value,
        "variables": [_localized_variable(v, locale) for v in tpl.variables],
        "default_options": _localized_default_options(tpl.default_options,
                                                       locale),
    }


def _full(tpl: ScenarioTemplate, locale: str) -> dict:
    out = _summary(tpl, locale)
    out["material_template"] = _pick_bilingual(tpl.material_template, locale)
    out["question_template"] = _pick_bilingual(tpl.question_template, locale)
    return out


class InstantiateRequest(BaseModel):
    values: dict[str, Any] = {}
    options: list[str] | None = None


@router.get("/templates")
def list_all(request: Request,
             tenant: TenantInfo = Depends(require_tenant)) -> list[dict]:
    loc = get_request_locale(request)
    return [_summary(tpl, loc) for tpl in list_templates()]


@router.get("/templates/{template_id}")
def get_one(template_id: str,
            request: Request,
            tenant: TenantInfo = Depends(require_tenant)) -> dict:
    loc = get_request_locale(request)
    try:
        tpl = load_template(template_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=t("request.template_not_found", locale=loc,
                     template_id=template_id))
    return _full(tpl, loc)


@router.post("/templates/{template_id}/instantiate")
def post_instantiate(
    template_id: str,
    body: InstantiateRequest,
    request: Request,
    tenant: TenantInfo = Depends(require_tenant),
) -> dict:
    loc = get_request_locale(request)
    try:
        tpl = load_template(template_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=t("request.template_not_found", locale=loc,
                     template_id=template_id))
    try:
        return instantiate(tpl, body.values, options=body.options, locale=loc)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=t("request.template_instantiate_failed",
                     locale=loc, error=str(e)))
