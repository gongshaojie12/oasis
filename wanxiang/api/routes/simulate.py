# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""POST /v1/simulate —— 端到端模拟同步端点。"""
from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException, Request

from wanxiang.api.auth import require_tenant
from wanxiang.api.deps import get_model_factory
from wanxiang.api.observability import metrics
from wanxiang.api.schemas import SimulateRequest, SimulateResponse
from wanxiang.api.tenancy import TenantInfo
from wanxiang.datasources import load_distribution
from wanxiang.media.environment import MediaItem
from wanxiang.personas import PersonaBuilder
from wanxiang.reporting import build_report, render_markdown
from wanxiang.simulation import (BatchRunner, DecisionKind, ScenarioConfig,
                                  SocialRoundsRunner, aggregate)


def _media_pool_from_payload(payload) -> tuple[MediaItem, ...]:
    """ScenarioPayload.media_pool (list[MediaItemPayload]) → tuple[MediaItem]."""
    items = getattr(payload, "media_pool", None) or ()
    return tuple(
        MediaItem(
            item_id=mi.item_id, title=mi.title, body=mi.body,
            channel=mi.channel, tags=tuple(mi.tags), author=mi.author,
        )
        for mi in items
    )

router = APIRouter()


async def run_simulation_pipeline(
    req: SimulateRequest,
    model_factory,
) -> SimulateResponse:
    """共享的端到端模拟流水线。

    供同步路由 (/v1/simulate) 和异步任务路由 (/v1/simulations/async) 复用。
    抛出普通异常（FileNotFoundError 等），由调用方决定如何转换：
      - 同步路由把 FileNotFoundError 转 HTTP 400；
      - 异步任务把任何异常装到 task.error 并标 FAILED。
    """
    started = time.monotonic()

    # 1. 分布加载（文件不存在 → FileNotFoundError）
    distribution = load_distribution(req.distribution_path)

    # 2. 造人
    pb = PersonaBuilder()
    personas = pb.sample(distribution, n=req.n, seed=req.seed)

    # 3. 场景（含 M4 media_pool）
    kind = DecisionKind(req.scenario.kind)
    scenario = ScenarioConfig(
        material=req.scenario.material,
        question=req.scenario.question,
        decision_kind=kind,
        options=tuple(req.scenario.options) if req.scenario.options else None,
        media_pool=_media_pool_from_payload(req.scenario),
        feed_k=req.scenario.feed_k,
    )

    # 4. 模型
    model_call = model_factory(req.model)

    # 4b. L3 平台方言（可选，仅 rounds>0 生效；未知 platform → 400）
    dialect = None
    if req.platform and req.rounds > 0:
        from wanxiang.actions.dialect import DialectLoader
        import os as _os
        dialect_dir = _os.path.join(
            _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
            "..", "actions", "l3_dialects")
        try:
            dialect = DialectLoader(dialect_dir).load(req.platform)
        except FileNotFoundError:
            raise HTTPException(
                status_code=400,
                detail=f"unknown platform: {req.platform}")

    # 5. 跑模拟（按 rounds 选 decision_only 或 social）
    if req.rounds == 0:
        runner = BatchRunner(decision_concurrency=req.concurrency)
        results = await runner.run_all(personas, scenario, model_call)
    else:
        social = SocialRoundsRunner(
            rounds=req.rounds, decision_concurrency=req.concurrency,
            dialect=dialect)
        results, _hist = await social.run(personas, scenario, model_call)

    # 6. 聚合 + 报告
    agg = aggregate(results)
    report = build_report(scenario=scenario, aggregate=agg,
                          persona_count=req.n)
    markdown = render_markdown(report)

    elapsed_ms = int((time.monotonic() - started) * 1000)
    return SimulateResponse(
        decision_kind=kind.value,
        n_total=agg.n_total, n_valid=agg.n_valid,
        error_count=agg.error_count, error_rate=agg.error_rate,
        report=report, markdown=markdown, elapsed_ms=elapsed_ms,
    )


@router.post("/simulate", response_model=SimulateResponse)
async def simulate(
    req: SimulateRequest,
    request: Request,
    model_factory=Depends(get_model_factory),
    tenant: TenantInfo = Depends(require_tenant),
):
    kind_label = req.scenario.kind
    metrics.inc("simulate.requested",
                {"kind": kind_label, "mode": "sync"})
    try:
        resp = await run_simulation_pipeline(req, model_factory)
        metrics.observe("simulate.elapsed_ms", resp.elapsed_ms,
                        {"kind": kind_label})
        # M3-10：成功的同步模拟也写计费事件
        from wanxiang.api.usage import build_usage_event
        usage_store = getattr(request.app.state, "usage_store", None)
        if usage_store is not None:
            evt = build_usage_event(
                tenant_id=tenant.tenant_id, request=req,
                response_kind=resp.decision_kind, status="done")
            usage_store.record(evt)
            metrics.observe("usage.cost_units", evt.cost_units,
                            {"mode": evt.mode,
                             "tenant_id": tenant.tenant_id})
        return resp
    except FileNotFoundError as e:
        raise HTTPException(status_code=400,
                            detail=f"distribution file not found: {e}")
