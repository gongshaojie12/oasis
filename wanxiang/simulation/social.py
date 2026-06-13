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
"""
from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from wanxiang.personas.persona import Persona
from wanxiang.simulation.aggregate import AggregateReport, aggregate
from wanxiang.simulation.batch import BatchRunner
from wanxiang.simulation.decision import DecisionResult, ModelCall
from wanxiang.simulation.scenario import DecisionKind, ScenarioConfig


def format_peer_signal(report: AggregateReport) -> str:
    """根据当前轮的群体分布，生成将注入到 scenario 的"同辈参考"文本。

    CHOOSE → "群体首选 X，份额 60%；其它：B 30%, C 10%"
    数值类  → "群体均值 6.8，中段 5–8"
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
        if others_txt:
            return f"群体首选 {top}，份额 {top_pct:.0f}%；其它：{others_txt}"
        return f"群体首选 {top}，份额 {top_pct:.0f}%"
    # 数值
    s = report.stats
    return (f"群体均值 {s.get('mean', 0):.1f}，"
            f"中段 {s.get('p25')}–{s.get('p75')}")


class SocialRoundsRunner:
    """跑 R 轮社交后再得到最终决策（甲方案）。

    rounds=0 退化为 decision_only（history 只有 1 个快照）。
    """

    def __init__(self, rounds: int, decision_concurrency: int = 16):
        if rounds < 0:
            raise ValueError("rounds must be >= 0")
        self.rounds = rounds
        self._batch = BatchRunner(decision_concurrency=decision_concurrency)

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

        for _ in range(self.rounds):
            report = aggregate(current)
            peer = format_peer_signal(report)
            augmented = replace(
                scenario,
                material=scenario.material + "\n【同辈参考】" + peer,
            )
            current = await self._batch.run_all(
                personas_list, augmented, model_call)
            history.append(current)

        return current, history
