# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""POST /v1/simulate —— 端到端模拟同步端点。"""
from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException, Request

from wanxiang.api.auth import require_tenant
from wanxiang.api.deps import get_model_factory
from wanxiang.api.i18n import DEFAULT_LOCALE, get_request_locale, t
from wanxiang.api.observability import metrics
from wanxiang.api.schemas import SimulateRequest, SimulateResponse
from wanxiang.api.tenancy import TenantInfo, resolve_effective_model
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
    *,
    moderator=None,
    locale: str = DEFAULT_LOCALE,
) -> SimulateResponse:
    """共享的端到端模拟流水线。

    供同步路由 (/v1/simulate) 和异步任务路由 (/v1/simulations/async) 复用。
    抛出普通异常（FileNotFoundError 等），由调用方决定如何转换：
      - 同步路由把 FileNotFoundError 转 HTTP 400；
      - 异步任务把任何异常装到 task.error 并标 FAILED。

    M3-12：可选传入 `moderator`（实现 ModeratorProtocol），当
    `req.compliance.moderate_material` 时审核 scenario.material。
    """
    started = time.monotonic()

    # M3-12 合规：material 审核（在加载分布/造人之前，失败立即返回）
    policy = getattr(req, "compliance", None)
    if policy is not None and policy.moderate_material:
        if moderator is None:
            from wanxiang.compliance.moderation import NoOpModerator
            moderator = NoOpModerator()
        from wanxiang.compliance.moderation import ModerationVerdict
        verdict = await moderator.check(req.scenario.material)
        if verdict.verdict == ModerationVerdict.UNSAFE:
            cats = ",".join(verdict.categories) if verdict.categories else "unsafe"
            raise HTTPException(
                status_code=400,
                detail=t("sim.material_flagged_by_moderator",
                         locale=locale, reason=cats))

    # 1. 分布加载（文件不存在 → FileNotFoundError）
    distribution = load_distribution(req.distribution_path)

    # 2. 造人（P5: 把 locale 传给 builder，让 trait key + value 对应语言）
    pb = PersonaBuilder()
    personas = pb.sample(distribution, n=req.n, seed=req.seed, locale=locale)

    # 3. 场景（含 M4 media_pool；P4: locale 控制 LLM prompt 语言）
    kind = DecisionKind(req.scenario.kind)
    scenario = ScenarioConfig(
        material=req.scenario.material,
        question=req.scenario.question,
        decision_kind=kind,
        options=tuple(req.scenario.options) if req.scenario.options else None,
        media_pool=_media_pool_from_payload(req.scenario),
        feed_k=req.scenario.feed_k,
        locale=locale,
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
                detail=t("sim.unknown_platform", locale=locale,
                         platform=req.platform))

    # 5. 跑模拟（按 rounds 选 decision_only 或 social）
    if req.rounds == 0:
        runner = BatchRunner(decision_concurrency=req.concurrency)
        results = await runner.run_all(personas, scenario, model_call)
    else:
        # M3+ 微信关系可见性：wechat 平台时构建小世界好友图，每个 focal
        # 在 social 轮次只看到自己好友的 L2 输出。其他平台保持全局公开广场。
        friend_graph = None
        persona_ids = None
        if req.platform == "wechat":
            from wanxiang.social_graph.graph import generate_small_world
            persona_ids = [str(p.agent_id) for p in personas]
            friend_graph = generate_small_world(
                persona_ids, k=6, rewire_p=0.1, seed=req.seed)
        social = SocialRoundsRunner(
            rounds=req.rounds, decision_concurrency=req.concurrency,
            dialect=dialect,
            friend_graph=friend_graph, persona_ids=persona_ids)
        results, _hist = await social.run(personas, scenario, model_call)

    # 6. 聚合 + 报告
    agg = aggregate(results)
    report = build_report(scenario=scenario, aggregate=agg,
                          persona_count=req.n, locale=locale)

    # M3-12 合规：DP 噪声 + PII 脱敏
    if policy is not None:
        # 6a. 暴露 aggregate 视图（mean + quartiles + n_valid）到 report，
        #     方便后续 DP 与下游可视化。
        agg_view = _aggregate_view_from_stats(agg.stats, agg.n_valid)
        if agg_view is not None:
            if policy.dp_epsilon is not None:
                from wanxiang.compliance.dp import apply_dp_to_aggregate
                agg_view = apply_dp_to_aggregate(
                    agg_view,
                    epsilon=policy.dp_epsilon,
                    sensitivity=policy.dp_sensitivity,
                )
                # 同步把 DP'd mean / p25 / p75 写回 recommendation，
                # 保持现有消费者的视图一致。
                rec = report.get("recommendation") or {}
                if "mean" in rec and agg_view.get("mean") is not None:
                    rec["mean"] = agg_view["mean"]
                if "confidence_band" in rec:
                    q = agg_view.get("quartiles") or {}
                    rec["confidence_band"] = (q.get("p25"), q.get("p75"))
                report["recommendation"] = rec
            report["aggregate"] = agg_view
        if policy.redact_pii:
            from wanxiang.compliance.pii import redact_report, redact_text
            report = redact_report(report)
            markdown = redact_text(render_markdown(report, locale=locale))
        else:
            markdown = render_markdown(report, locale=locale)
    else:
        markdown = render_markdown(report, locale=locale)

    elapsed_ms = int((time.monotonic() - started) * 1000)
    return SimulateResponse(
        decision_kind=kind.value,
        n_total=agg.n_total, n_valid=agg.n_valid,
        error_count=agg.error_count, error_rate=agg.error_rate,
        report=report, markdown=markdown, elapsed_ms=elapsed_ms,
    )


def _aggregate_view_from_stats(stats: dict, n_valid: int) -> dict | None:
    """Build a {mean, quartiles:{p25,p50,p75}, n_valid} dict from an
    AggregateReport.stats. Returns None for CHOOSE / empty aggregates."""
    if not stats or "mean" not in stats:
        return None
    return {
        "mean": stats.get("mean"),
        "quartiles": {
            "p25": stats.get("p25"),
            "p50": stats.get("median"),
            "p75": stats.get("p75"),
        },
        "n_valid": n_valid,
    }


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
    moderator = getattr(request.app.state, "moderator", None)
    # spec D3：请求未指定 model 时，回落到 tenant.default_model_config，
    # 再回落到 stub。pipeline 不感知 tenant，所以在这里把 req 改写一遍。
    if req.model is None:
        req = req.model_copy(update={
            "model": resolve_effective_model(None, tenant)})
    loc = get_request_locale(request)
    try:
        resp = await run_simulation_pipeline(
            req, model_factory, moderator=moderator, locale=loc)
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
        raise HTTPException(
            status_code=400,
            detail=t("sim.distribution_file_not_found",
                     locale=loc, path=str(e)))
