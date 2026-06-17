# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""GET /v1/usage/current & GET /v1/usage/monthly (M3-10)."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from wanxiang.api.auth import require_tenant
from wanxiang.api.auth_user import require_user
from wanxiang.api.i18n import get_request_locale, t
from wanxiang.api.tenancy import TenantInfo

router = APIRouter()


def _store(request: Request):
    return request.app.state.usage_store


# ---------- Legacy X-API-Key routes (kept for backward compat) ----------

@router.get("/usage/current")
def usage_current(request: Request,
                   tenant: TenantInfo = Depends(require_tenant)):
    now = datetime.now(timezone.utc)
    return _store(request).monthly(tenant.tenant_id, now.year, now.month)


@router.get("/usage/monthly")
def usage_monthly(
    request: Request,
    year: int = Query(..., ge=2020, le=2100),
    month: int = Query(..., ge=1, le=12),
    tenant: TenantInfo = Depends(require_tenant),
):
    try:
        return _store(request).monthly(tenant.tenant_id, year, month)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=t("request.invalid_usage_query",
                     locale=get_request_locale(request), error=str(e)))


# ---------- Workspace-scoped JWT routes (for SPA frontend) ----------

def _resolve_ws(slug, request, user):
    from wanxiang.api.routes.workspaces import _require_member
    ws = request.app.state.workspace_store.get_by_slug(slug)
    if not ws:
        raise HTTPException(
            status_code=404,
            detail=t("workspace.not_found",
                     locale=get_request_locale(request)))
    _require_member(request, ws.workspace_id, user.user_id,
                    get_request_locale(request))
    return ws


@router.get("/workspaces/{slug}/usage/current")
def ws_usage_current(slug: str, request: Request,
                       user=Depends(require_user)):
    ws = _resolve_ws(slug, request, user)
    now = datetime.now(timezone.utc)
    return _store(request).monthly(ws.workspace_id, now.year, now.month)


@router.get("/workspaces/{slug}/usage/monthly")
def ws_usage_monthly(
    slug: str,
    request: Request,
    year: int = Query(..., ge=2020, le=2100),
    month: int = Query(..., ge=1, le=12),
    user=Depends(require_user),
):
    ws = _resolve_ws(slug, request, user)
    try:
        return _store(request).monthly(ws.workspace_id, year, month)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=t("request.invalid_usage_query",
                     locale=get_request_locale(request), error=str(e)))
