# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""FastAPI 应用工厂。"""
from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from wanxiang.api.observability import (AccessLogMiddleware,
                                          RequestIdMiddleware,
                                          configure_logging, metrics)
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

    # M3-7：访问日志的 handler / 格式（JSON 模式由 WANXIANG_LOG_JSON=1 开启）
    configure_logging()

    # 启动时加载租户表（默认 demo 租户；生产由 WANXIANG_TENANTS_JSON 注入）
    app.state.tenant_store = TenantStore.from_env()
    # M3-6：WANXIANG_TASKS_DB 设置则启用 SQLite 持久化，否则进程内内存 store。
    db_path = os.environ.get("WANXIANG_TASKS_DB")
    if db_path:
        from wanxiang.api.task_store_sqlite import SqliteTaskStore
        app.state.task_store = SqliteTaskStore(db_path)
    else:
        from wanxiang.api.tasks import TaskStore
        app.state.task_store = TaskStore()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["x-tenant-id", "x-request-id"],
    )
    app.add_middleware(TenantHeaderMiddleware)
    # M3-7：先加 AccessLog（注册顺序 → AccessLog 在内层），
    # 再加 RequestId（在外层），这样 RequestIdMiddleware 先跑、
    # 把 request.state.request_id 准备好，AccessLog 读到。
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(RequestIdMiddleware)

    @app.get("/healthz")
    def healthz():
        return {"status": "ok", "version": app.version}

    # M3-7：Prometheus 风格指标抓取端点（非鉴权；生产用网络/防火墙限制）
    @app.get("/metrics")
    def metrics_endpoint():
        return metrics.snapshot()

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

    # M3-2：异步模拟任务路由（独立 try 块，不影响同步路由挂载）
    try:
        from wanxiang.api.routes.simulations import (
            router as simulations_router)
        app.include_router(simulations_router, prefix="/v1")
    except Exception:
        pass

    # M4：场景模板路由
    try:
        from wanxiang.api.routes.templates import router as templates_router
        app.include_router(templates_router, prefix="/v1")
    except Exception:
        pass

    # M3-8：NL 意图解析路由（POST /v1/chat/parse）
    try:
        from wanxiang.api.routes.chat import router as chat_router
        app.include_router(chat_router, prefix="/v1")
    except Exception:
        pass

    return app
