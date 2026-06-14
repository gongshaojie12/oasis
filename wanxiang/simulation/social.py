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

P4 i18n: format_peer_signal + per_focal_peer_signal 接受 locale；
SocialRoundsRunner.run() 读 scenario.locale 并向下游传播。
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


# P4 i18n: 双语短语库 — peer signal 文本片段。
_PEER_I18N = {
    "zh": {
        "no_peers": "（暂无同辈数据）",
        "choose_top_share": "{top}，份额 {top_pct:.0f}%",
        "others_others": "；其它：{others}",
        "rate_core": "均值 {mean:.1f}，中段 {p25}–{p75}",
        "group_choose_prefix": "群体首选 {core}",
        "group_rate_prefix": "群体{core}",
        # dialect-aware
        "strong": "你的好友圈里 {core}（强关系传播）",
        "none": "社区热门 {core}",
        "recommend": "算法推荐里 {core}",
        "following": "关注的人里 {core}",
        "hotscore": "热度榜 {core}",
        "fallback": "群体 {core}",
        "peer_label": "【同辈参考】",
    },
    "en": {
        "no_peers": "(no peer data yet)",
        "choose_top_share": "{top}, share {top_pct:.0f}%",
        "others_others": "; others: {others}",
        "rate_core": "mean {mean:.1f}, p25-p75 {p25}-{p75}",
        "group_choose_prefix": "Group top pick {core}",
        "group_rate_prefix": "Group {core}",
        "strong": "Among your friends: {core} (strong-tie spread)",
        "none": "Community trending: {core}",
        "recommend": "Algorithm recommends: {core}",
        "following": "From people you follow: {core}",
        "hotscore": "Hot ranking: {core}",
        "fallback": "Group {core}",
        "peer_label": "[Peer reference]",
    },
}


def _i18n(loc: str) -> dict:
    if loc not in ("zh", "en"):
        loc = "zh"
    return _PEER_I18N[loc]


def format_peer_signal(
    report: AggregateReport,
    dialect: PlatformDialect | None = None,
    locale: str = "zh",
) -> str:
    """根据当前轮的群体分布，生成将注入到 scenario 的"同辈参考"文本。

    无 dialect（默认，保持向后兼容）：
      CHOOSE → "群体首选 X，份额 60%；其它：B 30%, C 10%"
      数值类  → "群体均值 6.8，中段 5–8"

    带 dialect（L3 平台方言激活）：按 relationship + feed_algorithm 切换措辞，
    让不同平台的 peer signal 体现不同关系语义和分发机制。
    空报告  → 中立占位

    P4: locale="en" 切到英文措辞。
    """
    L = _i18n(locale)
    if report.kind is None or report.n_valid == 0:
        return L["no_peers"]

    if report.kind is DecisionKind.CHOOSE:
        share = report.stats.get("share", {})
        top = report.stats.get("top")
        top_pct = (share.get(top, 0.0) * 100)
        others = sorted(
            ((k, v) for k, v in share.items() if k != top),
            key=lambda kv: kv[1], reverse=True)
        others_txt = ", ".join(f"{k} {v * 100:.0f}%" for k, v in others)
        core_payload = L["choose_top_share"].format(top=top, top_pct=top_pct)
        if others_txt:
            core_payload += L["others_others"].format(others=others_txt)
        if dialect is None:
            return L["group_choose_prefix"].format(core=core_payload)
    else:
        s = report.stats
        core_payload = L["rate_core"].format(
            mean=s.get("mean", 0),
            p25=s.get("p25"), p75=s.get("p75"))
        if dialect is None:
            return L["group_rate_prefix"].format(core=core_payload)

    # ----- dialect-aware phrasing -----
    rel = dialect.relationship
    feed = dialect.feed_algorithm

    if rel == "strong":
        return L["strong"].format(core=core_payload)
    if rel == "none":
        return L["none"].format(core=core_payload)
    # rel == "weak"
    if feed == "recommend":
        return L["recommend"].format(core=core_payload)
    if feed == "following":
        return L["following"].format(core=core_payload)
    if feed == "hotscore":
        return L["hotscore"].format(core=core_payload)
    # 兜底
    return L["fallback"].format(core=core_payload)


def per_focal_peer_signal(
    focal_idx: int,
    all_results: list[DecisionResult],
    friend_graph: FriendGraph,
    persona_ids: list[str],
    dialect: PlatformDialect | None = None,
    locale: str = "zh",
) -> str:
    """M3+：只用 focal 的好友子集做聚合，再生成 peer signal。

    无朋友（或 focal 不在 persona_ids / graph 里） → 中立占位文本。
    P4: locale 透传给 format_peer_signal。
    """
    if focal_idx < 0 or focal_idx >= len(persona_ids):
        return format_peer_signal(
            AggregateReport(kind=None, n_total=0, n_valid=0,
                            error_count=0, error_rate=0.0, stats={}),
            dialect=dialect, locale=locale)
    focal_id = persona_ids[focal_idx]
    allowed = friend_graph.neighbors(focal_id) - {focal_id}
    if not allowed:
        return format_peer_signal(
            AggregateReport(kind=None, n_total=0, n_valid=0,
                            error_count=0, error_rate=0.0, stats={}),
            dialect=dialect, locale=locale)
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
            dialect=dialect, locale=locale)
    return format_peer_signal(aggregate(peers), dialect=dialect, locale=locale)


class SocialRoundsRunner:
    """跑 R 轮社交后再得到最终决策（甲方案）。

    rounds=0 退化为 decision_only（history 只有 1 个快照）。

    M3+ 微信好友可见性：传 friend_graph + persona_ids 时，每个 focal
    在 round>=1 只看到自己好友的子集（per-focal aggregate）。其他平台
    不传 graph，行为与之前完全一致（全局 aggregate）。

    P4: scenario.locale 决定 peer signal 注入语言。
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
        locale = getattr(scenario, "locale", "zh")
        peer_label = _i18n(locale)["peer_label"]
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
                    personas_list, scenario, current, model_call,
                    locale=locale, peer_label=peer_label)
            else:
                report = aggregate(current)
                peer = format_peer_signal(report, dialect=self.dialect,
                                            locale=locale)
                augmented = replace(
                    scenario,
                    material=scenario.material + "\n" + peer_label + peer,
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
        *,
        locale: str = "zh",
        peer_label: str = "【同辈参考】",
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
                locale=locale,
            )
            augmented = replace(
                scenario,
                material=scenario.material + "\n" + peer_label + peer,
            )
            async with sem:
                return await self._decision.run(p, augmented, model_call)

        return await asyncio.gather(*(
            one(i, p) for i, p in enumerate(personas_list)))
