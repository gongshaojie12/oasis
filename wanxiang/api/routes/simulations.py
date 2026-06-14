# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""POST /v1/simulations/async  —— 异步任务版（M3-2）。
GET /v1/simulations/{id} —— 查状态/结果。"""
from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from wanxiang.api.auth import require_tenant
from wanxiang.api.deps import get_model_factory
from wanxiang.api.i18n import DEFAULT_LOCALE, get_request_locale, t
from wanxiang.api.observability import metrics
from wanxiang.api.routes.simulate import run_simulation_pipeline
from wanxiang.api.schemas import (SimulateRequest, SweepCombo, SweepRequest,
                                   SweepResponse)
from wanxiang.api.sweep import (MAX_SWEEP_COMBOS, apply_combo, combo_id,
                                 expand_grid)
from wanxiang.api.tasks import SimulationTask, TaskStatus, TaskStore
from wanxiang.api.tenancy import TenantInfo, resolve_effective_model

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
                    tenant_id: str | None = None,
                    event_bus=None,
                    locale: str = DEFAULT_LOCALE) -> None:
    started_at = datetime.now(timezone.utc)
    store.update(task_id, status=TaskStatus.RUNNING, started_at=started_at)
    status_str = "failed"
    kind = req.scenario.kind
    # M3-11：发布 started 事件（即使没有 subscriber 也会进 history buffer）
    if event_bus is not None:
        try:
            event_bus.publish(task_id, "started", {
                "task_id": task_id, "n": req.n, "rounds": req.rounds,
                "kind": req.scenario.kind,
            })
        except Exception:  # noqa: BLE001
            pass
    try:
        result = await run_simulation_pipeline(req, model_factory,
                                                locale=locale)
        finished_at = datetime.now(timezone.utc)
        store.update(task_id, status=TaskStatus.DONE, result=result,
                     finished_at=finished_at)
        metrics.inc("simulate.completed", {"status": "done"})
        metrics.observe(
            "simulate.elapsed_ms_async",
            (finished_at - started_at).total_seconds() * 1000)
        status_str = "done"
        kind = result.decision_kind
        if event_bus is not None:
            try:
                event_bus.publish(task_id, "done", {
                    "task_id": task_id,
                    "n_valid": result.n_valid,
                    "n_total": result.n_total,
                })
            except Exception:  # noqa: BLE001
                pass
    except Exception as e:  # noqa: BLE001
        store.update(task_id, status=TaskStatus.FAILED, error=str(e),
                     finished_at=datetime.now(timezone.utc))
        metrics.inc("simulate.completed", {"status": "failed"})
        if event_bus is not None:
            try:
                event_bus.publish(task_id, "error", {
                    "task_id": task_id, "error": str(e),
                })
            except Exception:  # noqa: BLE001
                pass
    finally:
        # M3-11：任何情况下都关流，避免订阅者 hang
        if event_bus is not None:
            try:
                event_bus.close(task_id)
            except Exception:  # noqa: BLE001
                pass
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


def _dispatch_async_simulation(
    *, req: SimulateRequest, locale: str, tenant_id: str, task_id: str,
    model_factory, task_store: TaskStore, usage_store, event_bus,
) -> None:
    """Hand off the async simulation to either asyncio or Celery.

    Selected by ``WANXIANG_TASK_QUEUE`` env var:
    - ``"asyncio"`` (default) — schedule ``_run_task`` on the current event loop.
    - ``"celery"`` — enqueue ``wanxiang.run_simulation`` on the configured
      broker; in eager mode the call runs synchronously inside ``.delay()``.

    Single-process backward compat: when the env var is unset the behaviour
    is identical to the pre-Stage-1+2 implementation.
    """
    mode = os.environ.get("WANXIANG_TASK_QUEUE", "asyncio").lower()
    if mode == "celery":
        # Lazy import so single-process mode never pulls Celery in.
        from wanxiang.api.celery_tasks import run_simulation_task
        run_simulation_task.delay(
            request_dict=req.model_dump(),
            locale=locale,
            tenant_id=tenant_id,
            task_id=task_id,
        )
        return
    # Default: in-process asyncio
    asyncio.create_task(_run_task(
        task_store, task_id, req, model_factory,
        usage_store=usage_store, tenant_id=tenant_id,
        event_bus=event_bus, locale=locale))


@router.post("/simulations/async", status_code=status.HTTP_202_ACCEPTED)
async def create_async_simulation(
    req: SimulateRequest,
    request: Request,
    model_factory=Depends(get_model_factory),
    tenant: TenantInfo = Depends(require_tenant),
):
    # spec D3：请求未指定 model 时回落到 tenant 默认 → stub
    if req.model is None:
        req = req.model_copy(update={
            "model": resolve_effective_model(None, tenant)})
    store = _store(request)
    task = store.create(tenant.tenant_id, req)
    metrics.inc("simulate.requested",
                {"kind": req.scenario.kind, "mode": "async"})
    usage_store = getattr(request.app.state, "usage_store", None)
    event_bus = getattr(request.app.state, "event_bus", None)
    # P3: capture locale now so background task renders in the requester's
    # language (request.state goes away once the response is sent).
    locale = get_request_locale(request)
    _dispatch_async_simulation(
        req=req, locale=locale, tenant_id=tenant.tenant_id, task_id=task.id,
        model_factory=model_factory, task_store=store,
        usage_store=usage_store, event_bus=event_bus,
    )
    return _serialize(task)


@router.post("/simulations/sweep", response_model=SweepResponse)
async def sweep_simulations(
    req: SweepRequest,
    request: Request,
    model_factory=Depends(get_model_factory),
    tenant: TenantInfo = Depends(require_tenant),
):
    """M5: 变量笛卡尔展开 (同步)。

    把 variable_grid 笛卡尔积展开成 N 个 combo，依次复用
    run_simulation_pipeline 跑完，按 combo 写计费事件，最后聚合返回。
    单个 combo 失败不影响其它 combo（错误装到 combo.error）。
    """
    combos_values = expand_grid(req.variable_grid)
    total = len(combos_values)
    if total > MAX_SWEEP_COMBOS:
        loc = get_request_locale(request)
        raise HTTPException(
            status_code=400,
            detail=t("sim.sweep_too_many_combos", locale=loc,
                     n=total, limit=MAX_SWEEP_COMBOS))

    metrics.inc("simulate.requested",
                {"kind": req.scenario.kind, "mode": "sweep"})

    # spec D3：sweep 同样支持租户默认模型回落
    effective_model = resolve_effective_model(req.model, tenant)
    # 把 sweep 字段折成一个 base SimulateRequest，供每个 combo 复用
    base = SimulateRequest(
        distribution_path=req.distribution_path, n=req.n, seed=req.seed,
        scenario=req.scenario, rounds=req.rounds, platform=req.platform,
        model=effective_model,
    )

    usage_store = getattr(request.app.state, "usage_store", None)
    sweep_locale = get_request_locale(request)

    out_combos: list[SweepCombo] = []
    for values in combos_values:
        cid = combo_id(values)
        combo_req = apply_combo(base, values)
        try:
            result = await run_simulation_pipeline(combo_req, model_factory,
                                                    locale=sweep_locale)
            if usage_store is not None:
                from wanxiang.api.usage import build_usage_event
                evt = build_usage_event(
                    tenant_id=tenant.tenant_id, request=combo_req,
                    response_kind=result.decision_kind, status="done")
                usage_store.record(evt)
                metrics.observe("usage.cost_units", evt.cost_units,
                                {"mode": evt.mode,
                                 "tenant_id": tenant.tenant_id})
            out_combos.append(SweepCombo(
                combo_id=cid, values=values, task_id=None,
                result=result.model_dump(), error=None))
        except Exception as e:  # noqa: BLE001
            # 失败 combo 也按消耗计费（cost 已经发生）
            if usage_store is not None:
                try:
                    from wanxiang.api.usage import build_usage_event
                    evt = build_usage_event(
                        tenant_id=tenant.tenant_id, request=combo_req,
                        response_kind=combo_req.scenario.kind, status="failed")
                    usage_store.record(evt)
                except Exception:  # noqa: BLE001
                    pass
            out_combos.append(SweepCombo(
                combo_id=cid, values=values, task_id=None,
                result=None, error=str(e)))

    return SweepResponse(total_combos=total, combos=out_combos)


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
        raise HTTPException(
            status_code=404,
            detail=t("request.task_not_found",
                     locale=get_request_locale(request)))
    return _serialize(task)
