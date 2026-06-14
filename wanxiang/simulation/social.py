# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""SocialRoundsRunner: L1+L2 社交涌现的轻量实现（spec D10 甲方案 MVP）。

机制：
- Round 0: 全体 agent 跑 decision_only（无 peer signal），得到初始分布
- 计算 peer signal（"群体首选是青提，份额 60%" / "群体均值 6.8"）
- Round 1..R: 在 scenario.material 上追加 peer signal 文本，再次跑
- 返回 (final_results, history_per_round)
- final_results = history[-1]

这把"L2 社交互动 → 信号回流影响 L1 最终决策"用最小的钩子做出来；
完整 OASIS 风格的 Channel 多轮互动（peer-graph、私信、被种草过程）
是 V2 工作。本 MVP 已能展示"agent 互相影响"的差异化。

M3+ 微信关系可见性：当传入 friend_graph 时，每个 focal 只看到自己好友
的 L2 输出 — 与微信"非好友不可见"一致。其他平台保持全局公开广场。
"""
from __future__ import annotations

import asyncio
from dataclasses import replace
from typing import Iterable

from wanxiang.actions.dialect import PlatformDialect
from wanxiang.personas.persona import Persona
from wanxiang.simulation.aggregate import AggregateReport, aggregate
from wanxiang.simulation.batch import BatchRunner
from wanxiang.simulation.decision import (DecisionResult, DecisionRunner,
                                          ModelCall)
from wanxiang.simulation.scenario import DecisionKind, ScenarioConfig
from wanxiang.social_graph.graph import FriendGraph


def format_peer_signal(
    report: AggregateReport,
    dialect: PlatformDialect | None = None,
) -> str:
    """根据当前轮的群体分布，生成将注入到 scenario 的"同辈参考"文本。

    无 dialect（默认，保持向后兼容）：
      CHOOSE → "群体首选 X，份额 60%；其它：B 30%, C 10%"
      数值类  → "群体均值 6.8，中段 5–8"

    带 dialect（L3 平台方言激活）：按 relationship + feed_algorithm 切换措辞，
    让不同平台的 peer signal 体现不同关系语义和分发机制。
    空报告  → 中立占位
    """
    if report.kind is None or report.n_valid == 0:
        return "（暂无同辈数据）"

    if report.kind is DecisionKind.CHOOSE:
        share = report.stats.get("share", {})
        top = report.stats.get("top")
        top_pct = (share.get(top, 0.0) * 100)
        # 其它选项按份额降序
        others = sorted(
            ((k, v) for k, v in share.items() if k != top),
            key=lambda kv: kv[1], reverse=True)
        others_txt = ", ".join(f"{k} {v * 100:.0f}%" for k, v in others)
        core_payload = (
            f"{top}，份额 {top_pct:.0f}%"
            + (f"；其它：{others_txt}" if others_txt else ""))
        if dialect is None:
            return f"群体首选 {core_payload}"
    else:
        s = report.stats
        core_payload = (f"均值 {s.get('mean', 0):.1f}，"
                        f"中段 {s.get('p25')}–{s.get('p75')}")
        if dialect is None:
            return f"群体{core_payload}"

    # ----- dialect-aware phrasing -----
    rel = dialect.relationship
    feed = dialect.feed_algorithm

    if rel == "strong":
        # 微信类：强关系私域
        return f"你的好友圈里 {core_payload}（强关系传播）"
    if rel == "none":
        # Reddit 类社区：无关系，靠社区可见度
        return f"社区热门 {core_payload}"
    # rel == "weak"
    if feed == "recommend":
        return f"算法推荐里 {core_payload}"
    if feed == "following":
        return f"关注的人里 {core_payload}"
    if feed == "hotscore":
        return f"热度榜 {core_payload}"
    # 兜底
    return f"群体 {core_payload}"


def per_focal_peer_signal(
    focal_idx: int,
    all_results: list[DecisionResult],
    friend_graph: FriendGraph,
    persona_ids: list[str],
    dialect: PlatformDialect | None = None,
) -> str:
    """M3+：只用 focal 的好友子集做聚合，再生成 peer signal。

    无朋友（或 focal 不在 persona_ids / graph 里） → 中立占位文本。
    """
    if focal_idx < 0 or focal_idx >= len(persona_ids):
        return format_peer_signal(
            AggregateReport(kind=None, n_total=0, n_valid=0,
                            error_count=0, error_rate=0.0, stats={}),
            dialect=dialect)
    focal_id = persona_ids[focal_idx]
    allowed = friend_graph.neighbors(focal_id) - {focal_id}
    if not allowed:
        return format_peer_signal(
            AggregateReport(kind=None, n_total=0, n_valid=0,
                            error_count=0, error_rate=0.0, stats={}),
            dialect=dialect)
    peers = [
        r for i, r in enumerate(all_results)
        if i != focal_idx
        and i < len(persona_ids)
        and persona_ids[i] in allowed
    ]
    if not peers:
        return format_peer_signal(
            AggregateReport(kind=None, n_total=0, n_valid=0,
                            error_count=0, error_rate=0.0, stats={}),
            dialect=dialect)
    return format_peer_signal(aggregate(peers), dialect=dialect)


class SocialRoundsRunner:
    """跑 R 轮社交后再得到最终决策（甲方案）。

    rounds=0 退化为 decision_only（history 只有 1 个快照）。

    M3+ 微信好友可见性：传 friend_graph + persona_ids 时，每个 focal
    在 round>=1 只看到自己好友的子集（per-focal aggregate）。其他平台
    不传 graph，行为与之前完全一致（全局 aggregate）。
    """

    def __init__(
        self,
        rounds: int,
        decision_concurrency: int = 16,
        dialect: PlatformDialect | None = None,
        friend_graph: FriendGraph | None = None,
        persona_ids: list[str] | None = None,
    ):
        if rounds < 0:
            raise ValueError("rounds must be >= 0")
        if (friend_graph is None) != (persona_ids is None):
            raise ValueError(
                "friend_graph and persona_ids must be both provided or both None")
        self.rounds = rounds
        self.dialect = dialect
        self.friend_graph = friend_graph
        self.persona_ids = persona_ids
        self.decision_concurrency = decision_concurrency
        self._batch = BatchRunner(decision_concurrency=decision_concurrency)
        self._decision = DecisionRunner()

    async def run(
        self,
        personas: Iterable[Persona],
        scenario: ScenarioConfig,
        model_call: ModelCall,
    ) -> tuple[list[DecisionResult], list[list[DecisionResult]]]:
        personas_list = list(personas)
        # Round 0: 原始 scenario
        round0 = await self._batch.run_all(personas_list, scenario, model_call)
        history: list[list[DecisionResult]] = [round0]
        current = round0

        use_graph = (
            self.friend_graph is not None
            and self.persona_ids is not None
            and len(self.persona_ids) == len(personas_list)
        )

        for _ in range(self.rounds):
            if use_graph:
                current = await self._run_per_focal_round(
                    personas_list, scenario, current, model_call)
            else:
                report = aggregate(current)
                peer = format_peer_signal(report, dialect=self.dialect)
                augmented = replace(
                    scenario,
                    material=scenario.material + "\n【同辈参考】" + peer,
                )
                current = await self._batch.run_all(
                    personas_list, augmented, model_call)
            history.append(current)

        return current, history

    async def _run_per_focal_round(
        self,
        personas_list: list[Persona],
        scenario: ScenarioConfig,
        prev_round: list[DecisionResult],
        model_call: ModelCall,
    ) -> list[DecisionResult]:
        """每个 focal 用 only-friends 聚合的 peer signal 单独跑。"""
        assert self.friend_graph is not None and self.persona_ids is not None
        sem = asyncio.Semaphore(self.decision_concurrency)

        async def one(idx: int, p: Persona) -> DecisionResult:
            peer = per_focal_peer_signal(
                focal_idx=idx,
                all_results=prev_round,
                friend_graph=self.friend_graph,
                persona_ids=self.persona_ids,
                dialect=self.dialect,
            )
            augmented = replace(
                scenario,
                material=scenario.material + "\n【同辈参考】" + peer,
            )
            async with sem:
                return await self._decision.run(p, augmented, model_call)

        return await asyncio.gather(*(
            one(i, p) for i, p in enumerate(personas_list)))
