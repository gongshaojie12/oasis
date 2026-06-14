# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""GET /v1/audit/events — query tenant's audit log (M3-13)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from wanxiang.api.auth import require_tenant
from wanxiang.api.i18n import get_request_locale, t
from wanxiang.api.tenancy import TenantInfo

router = APIRouter()


def _store(request: Request):
    return request.app.state.audit_store


def _parse_iso(s: str | None, *, locale: str = "zh") -> datetime | None:
    if not s:
        return None
    try:
        d = datetime.fromisoformat(s)
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(
            400, t("audit.invalid_iso_datetime", locale=locale, value=s))


@router.get("/audit/events")
def audit_events(
    request: Request,
    start: Optional[str] = Query(None, description="ISO 8601 inclusive"),
    end: Optional[str] = Query(None, description="ISO 8601 exclusive"),
    action: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    tenant: TenantInfo = Depends(require_tenant),
):
    loc = get_request_locale(request)
    return _store(request).query(
        tenant.tenant_id,
        start=_parse_iso(start, locale=loc),
        end=_parse_iso(end, locale=loc),
        action=action, limit=limit,
    )
