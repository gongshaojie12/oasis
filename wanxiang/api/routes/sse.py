# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""SSE 进度流路由 (M3-11).

GET /v1/simulations/{task_id}/events
    返回 text/event-stream，订阅一个异步任务的实时进度。
    迟到的客户端会先收到历史事件（环形 buffer 重放），再切到 live。
    租户隔离：只能订阅自己 tenant 创建的 task；未知/非己 task → 404。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from wanxiang.api.auth import require_tenant
from wanxiang.api.tenancy import TenantInfo

router = APIRouter()


@router.get("/simulations/{task_id}/events")
async def simulation_events(
    task_id: str,
    request: Request,
    tenant: TenantInfo = Depends(require_tenant),
):
    task_store = request.app.state.task_store
    task = task_store.get(tenant.tenant_id, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")

    bus = request.app.state.event_bus

    async def generator():
        async for ev in bus.subscribe(task_id):
            if await request.is_disconnected():
                break
            yield ev.to_sse()

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # 关闭 nginx 缓冲
        },
    )
