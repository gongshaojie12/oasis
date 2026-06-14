# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""analyze_factor_contributions: 给基线 + 因子，输出贡献排名。"""
import asyncio

import pytest

from wanxiang.personas.persona import Persona
from wanxiang.reasoning.causal import (CausalReport, Factor,
                                         FactorContribution,
                                         analyze_factor_contributions)
from wanxiang.simulation.scenario import DecisionKind, ScenarioConfig


def _personas(n):
    return [Persona(agent_id=i, name=f"p{i}",
                    demographic={}, personality={}, media={})
            for i in range(n)]


def _smart_call_for_rate():
    """根据 material 里有没有关键词决定打分。
    含"0糖0卡"→8 分；含"小红书"→7 分；其它→5 分。
    """
    async def call(messages):
        m = messages[1]["content"]
        if "0糖0卡" in m and "小红书" in m:
            return '{"score": 9}'
        if "0糖0卡" in m:
            return '{"score": 8}'
        if "小红书" in m:
            return '{"score": 6}'
        return '{"score": 4}'
    return call


def test_returns_causal_report_with_ranked_contributions():
    scenario = ScenarioConfig(
        material="新品轻气泡，主打0糖0卡,小红书种草投放",
        question="0-10 评分",
        decision_kind=DecisionKind.RATE,
    )
    factors = [
        Factor(id="health", label="0糖0卡 健康卖点", snippet="0糖0卡"),
        Factor(id="channel", label="小红书 渠道", snippet="小红书种草投放"),
    ]
    r = asyncio.run(analyze_factor_contributions(
        scenario, factors, _personas(10), _smart_call_for_rate()))
    assert isinstance(r, CausalReport)
    assert len(r.contributions) == 2
    # baseline 应是 9（含两个关键词）；移除 health 后只有"小红书"→6（delta=3）
    # 移除 channel 后只有"0糖0卡"→8（delta=1）
    # 所以 health 的 abs_delta 更大 → 排第 1
    assert r.contributions[0].factor_id == "health"
    assert r.contributions[0].rank == 1
    assert r.contributions[1].factor_id == "channel"
    assert r.contributions[1].rank == 2
    assert r.contributions[0].abs_delta > r.contributions[1].abs_delta


def test_factor_snippet_not_in_material_is_noted_and_skipped():
    scenario = ScenarioConfig(
        material="新品轻气泡，主打0糖0卡",
        question="0-10 评分",
        decision_kind=DecisionKind.RATE)
    factors = [
        Factor(id="missing", label="并不存在的标签", snippet="不存在的字串xyz"),
        Factor(id="real", label="0糖0卡 卖点", snippet="0糖0卡"),
    ]
    r = asyncio.run(analyze_factor_contributions(
        scenario, factors, _personas(5), _smart_call_for_rate()))
    # missing 被跳过，只剩 real
    assert len(r.contributions) == 1
    assert r.contributions[0].factor_id == "real"
    assert any("missing" in n for n in r.notes)


def test_choose_kind_metric_is_top_share():
    """CHOOSE：用 baseline 的 top 选项的 share 作为 metric。"""
    async def call(messages):
        m = messages[1]["content"]
        # 含"魅力" → 大家选 A；不含 → 大家选 B
        if "魅力" in m:
            return '{"option": "A"}'
        return '{"option": "B"}'

    scenario = ScenarioConfig(
        material="A 方案有魅力，B 方案中性",
        question="选一个",
        decision_kind=DecisionKind.CHOOSE,
        options=("A", "B"))
    factors = [Factor(id="charm", label="A 的魅力", snippet="有魅力")]
    r = asyncio.run(analyze_factor_contributions(
        scenario, factors, _personas(10), call))
    # baseline A 几乎全选 → share≈1；ablated A 几乎不选 → share≈0
    # 但 metric 是"baseline 的 top（=A）的 share"
    assert r.contributions[0].baseline_metric > 0.9
    assert r.contributions[0].ablated_metric < 0.1


def test_empty_factors_returns_empty_contributions():
    scenario = ScenarioConfig(material="m", question="q",
                               decision_kind=DecisionKind.RATE)
    async def call(m): return '{"score": 5}'
    r = asyncio.run(analyze_factor_contributions(
        scenario, [], _personas(3), call))
    assert r.contributions == []
    assert r.baseline_metric is not None
