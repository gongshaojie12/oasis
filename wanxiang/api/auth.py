# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""FastAPI auth dependency: X-API-Key header -> TenantInfo, with RPM quota."""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Request

from wanxiang.api.i18n import DEFAULT_LOCALE, normalize_locale, t
from wanxiang.api.observability import metrics
from wanxiang.api.tenancy import TenantInfo, TenantStore


def get_tenant_store(request: Request) -> TenantStore:
    """Return the app-scoped TenantStore (set on app.state in create_app)."""
    return request.app.state.tenant_store


def _current_locale(request: Request) -> str:
    """Best-effort: read request.state.locale set by RequestLocaleMiddleware.

    Defensive: if the middleware never ran (tests using raw apps,
    early-failures), fall back to DEFAULT_LOCALE.
    """
    return getattr(request.state, "locale", None) or DEFAULT_LOCALE


def require_tenant(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    store: TenantStore = Depends(get_tenant_store),
) -> TenantInfo:
    loc = _current_locale(request)
    if not x_api_key:
        metrics.inc("auth.failure", {"reason": "missing"})
        raise HTTPException(
            status_code=401,
            detail=t("auth.missing_api_key", locale=loc))
    tenant = store.lookup(x_api_key)
    if tenant is None:
        metrics.inc("auth.failure", {"reason": "invalid_key"})
        raise HTTPException(
            status_code=401,
            detail=t("auth.invalid_api_key", locale=loc))
    # i18n P1: after auth, if neither body nor header explicitly provided a
    # locale, apply tenant's default_locale. This way tenant default wins
    # over the global zh fallback but does not override an explicit choice.
    body_provided = getattr(request.state, "locale_from_body", False)
    header_provided = getattr(request.state, "locale_from_header", False)
    if not body_provided and not header_provided:
        tenant_loc = normalize_locale(tenant.default_locale)
        if tenant_loc is not None:
            request.state.locale = tenant_loc
            loc = tenant_loc
    request.state.tenant_default_locale = tenant.default_locale

    bucket = store.bucket_for(tenant.tenant_id)
    if bucket is not None and not bucket.consume():
        retry = bucket.retry_after_seconds()
        metrics.inc("auth.rate_limited", {"tenant_id": tenant.tenant_id})
        raise HTTPException(
            status_code=429,
            detail=t("auth.rate_limit_exceeded", locale=loc,
                     tenant_id=tenant.tenant_id),
            headers={"Retry-After": str(retry)})
    # Stash on request.state so TenantHeaderMiddleware can echo it
    request.state.tenant_id = tenant.tenant_id
    metrics.inc("auth.success", {"tenant_id": tenant.tenant_id})
    return tenant
