# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""POST /v1/simulate —— 端到端模拟同步端点。"""
from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException

from wanxiang.api.auth import require_tenant
from wanxiang.api.deps import get_model_factory
from wanxiang.api.schemas import SimulateRequest, SimulateResponse
from wanxiang.api.tenancy import TenantInfo
from wanxiang.datasources import load_distribution
from wanxiang.personas import PersonaBuilder
from wanxiang.reporting import build_report, render_markdown
from wanxiang.simulation import (BatchRunner, DecisionKind, ScenarioConfig,
                                  SocialRoundsRunner, aggregate)

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

    # 3. 场景
    kind = DecisionKind(req.scenario.kind)
    scenario = ScenarioConfig(
        material=req.scenario.material,
        question=req.scenario.question,
        decision_kind=kind,
        options=tuple(req.scenario.options) if req.scenario.options else None,
    )

    # 4. 模型
    model_call = model_factory(req.model)

    # 5. 跑模拟（按 rounds 选 decision_only 或 social）
    if req.rounds == 0:
        runner = BatchRunner(decision_concurrency=req.concurrency)
        results = await runner.run_all(personas, scenario, model_call)
    else:
        social = SocialRoundsRunner(
            rounds=req.rounds, decision_concurrency=req.concurrency)
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
    model_factory=Depends(get_model_factory),
    tenant: TenantInfo = Depends(require_tenant),
):
    try:
        return await run_simulation_pipeline(req, model_factory)
    except FileNotFoundError as e:
        raise HTTPException(status_code=400,
                            detail=f"distribution file not found: {e}")
