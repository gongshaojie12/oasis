# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""FastAPI 应用工厂。"""
from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from wanxiang.api.tenancy import TenantStore


class TenantHeaderMiddleware(BaseHTTPMiddleware):
    """把租户 ID 透传到响应头。

    M3-3 起，request.state.tenant_id 由 require_tenant 鉴权依赖写入，是权威来源；
    客户端自带的 X-Tenant-Id 不再被 /v1/* 信任。对于不需要鉴权的路径
    （/healthz、/、/prototype/*）保留 M3-1 的 passthrough 行为以兼容旧客户端。
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        tenant_id = getattr(request.state, "tenant_id", None)
        if tenant_id is not None:
            response.headers["x-tenant-id"] = tenant_id
        elif request.headers.get("x-tenant-id"):
            response.headers["x-tenant-id"] = request.headers["x-tenant-id"]
        return response


def create_app() -> FastAPI:
    app = FastAPI(title="WANXIANG API",
                  description="万象人群模拟预测平台 API",
                  version="0.0.1")

    # 启动时加载租户表（默认 demo 租户；生产由 WANXIANG_TENANTS_JSON 注入）
    app.state.tenant_store = TenantStore.from_env()

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
