# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""GET /v1/usage/current & GET /v1/usage/monthly (M3-10)."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from wanxiang.api.auth import require_tenant
from wanxiang.api.i18n import get_request_locale, t
from wanxiang.api.tenancy import TenantInfo

router = APIRouter()


def _store(request: Request):
    return request.app.state.usage_store


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
