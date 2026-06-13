# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""FastAPI 应用工厂。"""
from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware


class TenantHeaderMiddleware(BaseHTTPMiddleware):
    """把请求头 X-Tenant-Id 透传到响应；M3-1 只透传，M3-3 才做真隔离。"""

    async def dispatch(self, request: Request, call_next):
        tenant = request.headers.get("x-tenant-id")
        response = await call_next(request)
        if tenant:
            response.headers["x-tenant-id"] = tenant
        return response


def create_app() -> FastAPI:
    app = FastAPI(title="WANXIANG API",
                  description="万象人群模拟预测平台 API",
                  version="0.0.1")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["x-tenant-id"],
    )
    app.add_middleware(TenantHeaderMiddleware)

    @app.get("/healthz")
    def healthz():
        return {"status": "ok", "version": app.version}

    # M3-4：挂载 docs/prototype 静态资源，让 chat.html 与 /v1/simulate 同源。
    _PROTOTYPE_DIR = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "docs",
                     "prototype"))
    if os.path.isdir(_PROTOTYPE_DIR):
        chat_html = os.path.join(_PROTOTYPE_DIR, "chat.html")
        if os.path.isfile(chat_html):

            @app.get("/", include_in_schema=False)
            def root():
                return FileResponse(chat_html, media_type="text/html")

        app.mount("/prototype",
                  StaticFiles(directory=_PROTOTYPE_DIR, html=True),
                  name="prototype")

    # simulate 路由由 Task 3 挂载；若 routes.simulate 未存在则跳过，
    # 这样 Task 2 完成而 Task 3 未做时 app 仍可启动。
    try:
        from wanxiang.api.routes.simulate import router as simulate_router
        app.include_router(simulate_router, prefix="/v1")
    except Exception:
        pass

    return app
