# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""POST /v1/simulations/async  —— 异步任务版（M3-2）。
GET /v1/simulations/{id} —— 查状态/结果。"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from wanxiang.api.auth import require_tenant
from wanxiang.api.deps import get_model_factory
from wanxiang.api.observability import metrics
from wanxiang.api.routes.simulate import run_simulation_pipeline
from wanxiang.api.schemas import SimulateRequest
from wanxiang.api.tasks import SimulationTask, TaskStatus, TaskStore
from wanxiang.api.tenancy import TenantInfo

router = APIRouter()


def _store(request: Request) -> TaskStore:
    return request.app.state.task_store


def _serialize(task: SimulationTask) -> dict:
    return {
        "task_id": task.id,
        "status": task.status.value,
        "created_at": task.created_at.isoformat(),
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "finished_at": task.finished_at.isoformat() if task.finished_at else None,
        "result": task.result.model_dump() if task.result is not None else None,
        "error": task.error,
    }


async def _run_task(store: TaskStore, task_id: str, req: SimulateRequest,
                    model_factory, usage_store=None,
                    tenant_id: str | None = None) -> None:
    started_at = datetime.now(timezone.utc)
    store.update(task_id, status=TaskStatus.RUNNING, started_at=started_at)
    status_str = "failed"
    kind = req.scenario.kind
    try:
        result = await run_simulation_pipeline(req, model_factory)
        finished_at = datetime.now(timezone.utc)
        store.update(task_id, status=TaskStatus.DONE, result=result,
                     finished_at=finished_at)
        metrics.inc("simulate.completed", {"status": "done"})
        metrics.observe(
            "simulate.elapsed_ms_async",
            (finished_at - started_at).total_seconds() * 1000)
        status_str = "done"
        kind = result.decision_kind
    except Exception as e:  # noqa: BLE001
        store.update(task_id, status=TaskStatus.FAILED, error=str(e),
                     finished_at=datetime.now(timezone.utc))
        metrics.inc("simulate.completed", {"status": "failed"})
    # M3-10：无论成功/失败都写一条计费事件（cost 已经发生）
    if usage_store is not None and tenant_id is not None:
        try:
            from wanxiang.api.usage import build_usage_event
            evt = build_usage_event(
                tenant_id=tenant_id, request=req,
                response_kind=kind, status=status_str, task_id=task_id)
            usage_store.record(evt)
            metrics.observe("usage.cost_units", evt.cost_units,
                            {"mode": evt.mode, "tenant_id": tenant_id})
        except Exception:  # noqa: BLE001
            # 计费失败不应影响任务结果
            pass


@router.post("/simulations/async", status_code=status.HTTP_202_ACCEPTED)
async def create_async_simulation(
    req: SimulateRequest,
    request: Request,
    model_factory=Depends(get_model_factory),
    tenant: TenantInfo = Depends(require_tenant),
):
    store = _store(request)
    task = store.create(tenant.tenant_id, req)
    metrics.inc("simulate.requested",
                {"kind": req.scenario.kind, "mode": "async"})
    usage_store = getattr(request.app.state, "usage_store", None)
    # 后台跑；同步立即返
    asyncio.create_task(_run_task(
        store, task.id, req, model_factory,
        usage_store=usage_store, tenant_id=tenant.tenant_id))
    return _serialize(task)


@router.get("/simulations")
async def list_simulations(
    request: Request,
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    tenant: TenantInfo = Depends(require_tenant),
):
    store = _store(request)
    tasks = store.list_for_tenant(tenant.tenant_id, limit=limit, offset=offset)
    return [_serialize(t) for t in tasks]


@router.get("/simulations/{task_id}")
async def get_simulation_task(
    task_id: str,
    request: Request,
    tenant: TenantInfo = Depends(require_tenant),
):
    store = _store(request)
    task = store.get(tenant.tenant_id, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return _serialize(task)
