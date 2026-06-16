# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""FastAPI 应用工厂。"""
from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from wanxiang.api.api_keys import make_api_key_store
from wanxiang.api.bootstrap import (ensure_demo_workspace_and_key,
                                       ensure_super_admin)
from wanxiang.api.observability import (AccessLogMiddleware,
                                          RequestIdMiddleware,
                                          configure_logging, metrics)
from wanxiang.api.server import ServerSettings
from wanxiang.api.tenancy import TenantStore
from wanxiang.api.email import make_email_service
from wanxiang.api.sms import make_sms_service
from wanxiang.api.users import make_user_store
from wanxiang.api.verification import make_verification_store
from wanxiang.api.workspaces import make_workspace_store


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
    # P1: ServerSettings exposed on app.state for brand/JWT config + new deps
    app.state.settings = ServerSettings()
    app.state.user_store = make_user_store(
        os.environ.get("WANXIANG_TASKS_DB"))
    app.state.workspace_store = make_workspace_store(
        os.environ.get("WANXIANG_TASKS_DB"))
    # P3: api_key store + bootstrap default demo workspace/api_key
    app.state.api_key_store = make_api_key_store(
        os.environ.get("WANXIANG_TASKS_DB"))
    try:
        ensure_demo_workspace_and_key(
            user_store=app.state.user_store,
            workspace_store=app.state.workspace_store,
            api_key_store=app.state.api_key_store,
        )
    except Exception as _e:  # pragma: no cover (defensive — never break boot)
        import logging as _logging
        _logging.getLogger(__name__).warning(
            "bootstrap demo workspace/api_key failed: %s", _e)
    # P4: optionally create super-admin from WANXIANG_SUPER_ADMIN_EMAIL/PASSWORD
    try:
        ensure_super_admin(user_store=app.state.user_store)
    except Exception as _e:  # pragma: no cover
        import logging as _logging
        _logging.getLogger(__name__).warning(
            "bootstrap super-admin failed: %s", _e)
    # P2: SMS / Email / verification code stores + services.
    # Default env stays NoOp (logs to stdout) — production wires real
    # provider via WANXIANG_SMS_PROVIDER / WANXIANG_EMAIL_PROVIDER.
    app.state.sms_service = make_sms_service()
    app.state.email_service = make_email_service()
    app.state.verification_store = make_verification_store(
        os.environ.get("WANXIANG_TASKS_DB"))
    # M3-6 / M3-9：WANXIANG_TASKS_DB 接受 DSN（None/plain-path/sqlite:///.../postgresql://...）。
    from wanxiang.api.tasks import make_task_store
    app.state.task_store = make_task_store(os.environ.get("WANXIANG_TASKS_DB"))
    # M3-10：真计费——usage store 与 task store 共享同一 DSN（两张独立表）。
    from wanxiang.api.usage import make_usage_store
    app.state.usage_store = make_usage_store(
        os.environ.get("WANXIANG_TASKS_DB"))
    # M3-13：审计日志 store 与 task/usage store 复用同一 DSN（独立 audit_events 表）。
    from wanxiang.api.audit import make_audit_store
    app.state.audit_store = make_audit_store(
        os.environ.get("WANXIANG_TASKS_DB"))
    # P4：余额流水 store —— 与其他 store 共享同一 DSN（独立 transactions 表）。
    from wanxiang.api.transactions import make_transaction_store
    app.state.transaction_store = make_transaction_store(
        os.environ.get("WANXIANG_TASKS_DB"))
    # M3-11 / Stage 1+2: SSE 事件总线。
    # 默认 in-memory；设置 WANXIANG_EVENT_BUS=redis 后切到跨进程 Redis 实现。
    from wanxiang.api.events import get_event_bus
    app.state.event_bus = get_event_bus()
    # M3-12：默认内容审核器（NoOp）。生产可注入 KeywordBlocklistModerator
    # 或云厂商 moderation 实现。
    from wanxiang.compliance.moderation import NoOpModerator
    app.state.moderator = NoOpModerator()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["x-tenant-id", "x-request-id"],
    )
    app.add_middleware(TenantHeaderMiddleware)
    # M3-13：审计中间件 — 在 AccessLog 之前注册（更内层），这样它先观察到
    # 路由的 response.status_code，再让 AccessLog/RequestId 包裹。
    from wanxiang.api.audit_middleware import AuditMiddleware
    app.add_middleware(AuditMiddleware)
    # i18n P1：locale 中间件 — 在 auth 依赖之前已跑过，写 request.state.locale。
    # 注册顺序：在 AccessLog 之前（更内层），这样 auth 依赖能读到它的输出。
    from wanxiang.api.locale_middleware import RequestLocaleMiddleware
    app.add_middleware(RequestLocaleMiddleware)
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

    # M3-11：SSE 进度流路由
    try:
        from wanxiang.api.routes.sse import router as sse_router
        app.include_router(sse_router, prefix="/v1")
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

    # M6：因果归因 + 反事实推演端点
    try:
        from wanxiang.api.routes.reasoning import router as reasoning_router
        app.include_router(reasoning_router, prefix="/v1")
    except Exception:
        pass

    # M3-10：真计费查询端点
    try:
        from wanxiang.api.routes.usage import router as usage_router
        app.include_router(usage_router, prefix="/v1")
    except Exception:
        pass

    # M3-13：审计日志查询端点
    try:
        from wanxiang.api.routes.audit import router as audit_router
        app.include_router(audit_router, prefix="/v1")
    except Exception:
        pass

    # M6+：报告 PDF 导出端点
    try:
        from wanxiang.api.routes.reports import router as reports_router
        app.include_router(reports_router, prefix="/v1")
    except Exception:
        pass

    # P1: user auth routes (/v1/auth/{register,login,refresh,logout},
    # /v1/me, /v1/brand). Independent try block so failures don't break
    # legacy X-API-Key routes above.
    try:
        from wanxiang.api.routes.auth import router as auth_router
        app.include_router(auth_router, prefix="/v1")
    except Exception:
        pass

    # P2: verification code routes (send/verify email + SMS)
    try:
        from wanxiang.api.routes.verify import router as verify_router
        app.include_router(verify_router, prefix="/v1")
    except Exception:
        pass

    # P3: workspace CRUD + member + invite + api-key management
    try:
        from wanxiang.api.routes.workspaces import router as ws_router
        app.include_router(ws_router, prefix="/v1")
    except Exception:
        pass
    try:
        from wanxiang.api.routes.api_keys import router as ak_router
        app.include_router(ak_router, prefix="/v1")
    except Exception:
        pass

    # P4: super-admin routes (/v1/admin/*) + workspace-scoped billing
    try:
        from wanxiang.api.routes.admin import router as admin_router
        app.include_router(admin_router, prefix="/v1")
    except Exception:
        pass
    try:
        from wanxiang.api.routes.billing import router as billing_router
        app.include_router(billing_router, prefix="/v1")
    except Exception:
        pass

    return app
