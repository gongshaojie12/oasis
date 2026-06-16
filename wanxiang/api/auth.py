# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""FastAPI auth dependency: X-API-Key header -> TenantInfo, with RPM quota.

P3: now resolves api keys via app.state.api_key_store first (PG-backed
workspace api_keys). The legacy in-memory TenantStore (env-based) is kept
as a fallback so old test fixtures that monkey-patch ``app.state.tenant_store``
keep working. ``TenantInfo.tenant_id`` is set to the workspace_id in the
new path — existing routes don't care about the semantic shift.
"""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Request

from wanxiang.api.i18n import DEFAULT_LOCALE, normalize_locale, t
from wanxiang.api.observability import metrics
from wanxiang.api.tenancy import TenantInfo, TenantStore, TokenBucket


def get_tenant_store(request: Request) -> TenantStore:
    """Return the app-scoped TenantStore (set on app.state in create_app)."""
    return request.app.state.tenant_store


def _current_locale(request: Request) -> str:
    """Best-effort: read request.state.locale set by RequestLocaleMiddleware.

    Defensive: if the middleware never ran (tests using raw apps,
    early-failures), fall back to DEFAULT_LOCALE.
    """
    return getattr(request.state, "locale", None) or DEFAULT_LOCALE


def _apply_locale_defaults(request: Request, default_locale: str,
                            current: str) -> str:
    """Mirror the legacy behaviour: if neither body nor header explicitly
    provided a locale, fall back to the tenant's default."""
    body_provided = getattr(request.state, "locale_from_body", False)
    header_provided = getattr(request.state, "locale_from_header", False)
    if not body_provided and not header_provided:
        tenant_loc = normalize_locale(default_locale)
        if tenant_loc is not None:
            request.state.locale = tenant_loc
            return tenant_loc
    request.state.tenant_default_locale = default_locale
    return current


def _get_or_make_bucket(request: Request, key_id: str,
                         rpm_limit: int) -> TokenBucket:
    """Stash per-api-key token buckets on app.state."""
    buckets = getattr(request.app.state, "_api_key_buckets", None)
    if buckets is None:
        buckets = {}
        request.app.state._api_key_buckets = buckets
    bucket = buckets.get(key_id)
    if bucket is None:
        bucket = TokenBucket(rpm_limit)
        buckets[key_id] = bucket
    return bucket


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

    # P3: lookup via api_key_store (PG-backed) first
    ak_store = getattr(request.app.state, "api_key_store", None)
    if ak_store is not None:
        ak = ak_store.lookup(x_api_key)
        if ak is not None:
            ws_store = getattr(request.app.state, "workspace_store", None)
            ws = ws_store.get_workspace(ak.workspace_id) if ws_store else None
            tenant_locale = ws.locale if ws else "zh"
            tenant = TenantInfo(
                tenant_id=ak.workspace_id,
                api_key=x_api_key,
                rpm_limit=ak.rpm_limit,
                monthly_budget=ak.monthly_budget or 0,
                default_model_config=None,
                default_locale=tenant_locale,
            )
            loc = _apply_locale_defaults(request, tenant_locale, loc)
            bucket = _get_or_make_bucket(request, ak.key_id, ak.rpm_limit)
            if not bucket.consume():
                retry = bucket.retry_after_seconds()
                metrics.inc("auth.rate_limited",
                             {"tenant_id": tenant.tenant_id})
                raise HTTPException(
                    status_code=429,
                    detail=t("auth.rate_limit_exceeded", locale=loc,
                              tenant_id=tenant.tenant_id),
                    headers={"Retry-After": str(retry)})
            request.state.tenant_id = tenant.tenant_id
            request.state.workspace = ws
            request.state.api_key_obj = ak
            metrics.inc("auth.success", {"tenant_id": tenant.tenant_id})
            return tenant

    # Legacy fallback (in-memory env-based TenantStore)
    tenant = store.lookup(x_api_key)
    if tenant is None:
        metrics.inc("auth.failure", {"reason": "invalid_key"})
        raise HTTPException(
            status_code=401,
            detail=t("auth.invalid_api_key", locale=loc))
    loc = _apply_locale_defaults(request, tenant.default_locale, loc)
    bucket = store.bucket_for(tenant.tenant_id)
    if bucket is not None and not bucket.consume():
        retry = bucket.retry_after_seconds()
        metrics.inc("auth.rate_limited", {"tenant_id": tenant.tenant_id})
        raise HTTPException(
            status_code=429,
            detail=t("auth.rate_limit_exceeded", locale=loc,
                     tenant_id=tenant.tenant_id),
            headers={"Retry-After": str(retry)})
    request.state.tenant_id = tenant.tenant_id
    metrics.inc("auth.success", {"tenant_id": tenant.tenant_id})
    return tenant
