# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""Set request.state.locale from request body / Accept-Language / tenant default / fallback."""
from __future__ import annotations

import json

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from wanxiang.api.i18n import (DEFAULT_LOCALE, Locale, normalize_locale,
                                 parse_accept_language)


# Paths that bypass locale resolution (no body, no auth context relevant)
_SKIP_PATHS = {"/healthz", "/metrics", "/"}


class RequestLocaleMiddleware(BaseHTTPMiddleware):
    """Resolves locale per request, exposed via request.state.locale.

    Priority (highest first):
      1. Request body ``locale`` field (POST/PUT/PATCH JSON; peek without
         consuming stream)
      2. HTTP ``Accept-Language`` header
      3. Tenant's ``default_locale`` (set by ``require_tenant`` onto
         request.state.tenant_default_locale at auth time)
      4. DEFAULT_LOCALE ("zh")

    Note: tenant default cannot be applied here for /v1/* routes because
    ``require_tenant`` runs AFTER the middleware. The auth dep itself
    will downgrade request.state.locale to tenant default when both
    body and header missed (see ``require_tenant``).
    """
    async def dispatch(self, request: Request, call_next):
        if request.url.path in _SKIP_PATHS:
            request.state.locale = DEFAULT_LOCALE
            return await call_next(request)
        loc: Locale | None = None
        body_provided = False
        header_provided = False
        # 1) Body locale field (only for POST/PUT/PATCH with JSON)
        if request.method in {"POST", "PUT", "PATCH"}:
            ctype = request.headers.get("content-type", "")
            if "application/json" in ctype:
                try:
                    body = await request.body()
                    # Re-attach body for downstream consumers
                    async def receive():
                        return {"type": "http.request", "body": body,
                                  "more_body": False}
                    request._receive = receive  # type: ignore
                    if body:
                        data = json.loads(body)
                        if isinstance(data, dict) and "locale" in data:
                            body_provided = True
                            loc = normalize_locale(data.get("locale"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass
        # 2) Accept-Language header
        if loc is None:
            header_raw = request.headers.get("accept-language")
            if header_raw:
                header_provided = True
                loc = parse_accept_language(header_raw)
        # Mark which sources were explicitly given vs fell through
        request.state.locale_from_body = body_provided
        request.state.locale_from_header = header_provided
        # 3/4) Tenant default applied later by require_tenant; fallback here
        if loc is None:
            loc = DEFAULT_LOCALE
        request.state.locale = loc
        return await call_next(request)
