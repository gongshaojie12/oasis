# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""中间件: 写操作自动记录 audit api_call 事件 (M3-13)."""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from wanxiang.api.audit import build_api_call_event

# 只记录写操作 + 健康检查/metrics 跳过
_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_SKIP_PATHS = {"/healthz", "/metrics", "/", "/prototype"}


class AuditMiddleware(BaseHTTPMiddleware):
    """Records audit_events for non-trivial writes."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.method not in _WRITE_METHODS:
            return response
        path = request.url.path
        if any(path == p or path.startswith(p + "/") for p in _SKIP_PATHS):
            return response
        # tenant lookup (only if auth succeeded; otherwise skip)
        tenant_id = getattr(request.state, "tenant_id", None)
        if tenant_id is None:
            # fall back to header→tenant lookup. For request bodies that fail
            # validation (422), auth dependency never runs; we still want to
            # audit the attempt if the API key is valid.
            api_key = request.headers.get("X-API-Key")
            tenant_store = getattr(request.app.state, "tenant_store", None)
            if api_key and tenant_store is not None:
                tenant = tenant_store.lookup(api_key)
                if tenant is not None:
                    tenant_id = tenant.tenant_id
        if tenant_id is None:
            return response
        request_id = (getattr(request.state, "request_id", None)
                      or response.headers.get("x-request-id"))
        try:
            request.app.state.audit_store.record(build_api_call_event(
                tenant_id=tenant_id, request=request,
                response_status=response.status_code,
                request_id=request_id))
        except Exception:
            # never block request on audit failure
            pass
        return response
