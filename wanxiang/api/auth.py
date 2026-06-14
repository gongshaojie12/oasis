# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""FastAPI auth dependency: X-API-Key header → TenantInfo, with RPM quota."""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Request

from wanxiang.api.observability import metrics
from wanxiang.api.tenancy import TenantInfo, TenantStore


def get_tenant_store(request: Request) -> TenantStore:
    """Return the app-scoped TenantStore (set on app.state in create_app)."""
    return request.app.state.tenant_store


def require_tenant(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    store: TenantStore = Depends(get_tenant_store),
) -> TenantInfo:
    if not x_api_key:
        metrics.inc("auth.failure", {"reason": "missing"})
        raise HTTPException(status_code=401,
                            detail="missing X-API-Key header")
    tenant = store.lookup(x_api_key)
    if tenant is None:
        metrics.inc("auth.failure", {"reason": "invalid_key"})
        raise HTTPException(status_code=401, detail="invalid api key")
    bucket = store.bucket_for(tenant.tenant_id)
    if bucket is not None and not bucket.consume():
        retry = bucket.retry_after_seconds()
        metrics.inc("auth.rate_limited", {"tenant_id": tenant.tenant_id})
        raise HTTPException(
            status_code=429,
            detail=f"rpm quota exceeded for tenant {tenant.tenant_id}",
            headers={"Retry-After": str(retry)})
    # Stash on request.state so TenantHeaderMiddleware can echo it
    request.state.tenant_id = tenant.tenant_id
    metrics.inc("auth.success", {"tenant_id": tenant.tenant_id})
    return tenant
