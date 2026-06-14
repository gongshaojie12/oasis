# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""compare_alternatives: 基线 + N 个替代方案 → 对比结果。"""
import asyncio

import pytest

from wanxiang.personas.persona import Persona
from wanxiang.reasoning.counterfactual import (Alternative,
                                                  AlternativeOutcome,
                                                  CounterfactualReport,
                                                  compare_alternatives)
from wanxiang.simulation.scenario import DecisionKind, ScenarioConfig


def _personas(n):
    return [Persona(agent_id=i, name=f"p{i}",
                    demographic={}, personality={}, media={})
            for i in range(n)]


def _smart_call():
    """评分按 material 关键词：含'¥6'→6，含'¥10'→3，否则 5。"""
    async def call(messages):
        m = messages[1]["content"]
        if "¥6" in m: return '{"score": 6}'
        if "¥10" in m: return '{"score": 3}'
        return '{"score": 5}'
    return call


def test_compare_baseline_and_two_alts():
    baseline_sc = ScenarioConfig(
        material="新品定价 ¥6", question="0-10 评分",
        decision_kind=DecisionKind.RATE)
    alts = [
        Alternative(id="cheaper", label="降到 ¥5",
                    material_override="新品定价 ¥5"),
        Alternative(id="pricier", label="涨到 ¥10",
                    material_override="新品定价 ¥10"),
    ]
    r = asyncio.run(compare_alternatives(
        (baseline_sc, "原价"), alts, _personas(5), _smart_call()))
    assert isinstance(r, CounterfactualReport)
    assert r.baseline_label == "原价"
    assert r.baseline_metric == 6.0  # 含 ¥6
    assert len(r.outcomes) == 2
    ids = {o.alt_id for o in r.outcomes}
    assert ids == {"cheaper", "pricier"}
    pricier = next(o for o in r.outcomes if o.alt_id == "pricier")
    assert pricier.metric == 3.0  # 含 ¥10
    assert pricier.delta_vs_baseline == pytest.approx(-3.0)


def test_alternative_with_only_question_override():
    baseline_sc = ScenarioConfig(
        material="¥6", question="A 问法", decision_kind=DecisionKind.RATE)
    alt = Alternative(id="rephrase", label="改问法",
                       question_override="B 问法")
    r = asyncio.run(compare_alternatives(
        (baseline_sc, "原"), [alt], _personas(3), _smart_call()))
    # material 仍含 ¥6 → metric 仍 6
    assert r.outcomes[0].metric == 6.0


def test_no_alternatives_returns_empty_outcomes():
    baseline_sc = ScenarioConfig(material="¥6", question="q",
                                   decision_kind=DecisionKind.RATE)
    r = asyncio.run(compare_alternatives(
        (baseline_sc, "原"), [], _personas(3), _smart_call()))
    assert r.outcomes == []
    assert r.baseline_metric == 6.0


def test_choose_alternative_with_options_override():
    async def call(messages):
        m = messages[1]["content"]
        if "甲" in m: return '{"option": "甲"}'
        return '{"option": "A"}'

    baseline_sc = ScenarioConfig(
        material="A 还是 B？", question="选",
        decision_kind=DecisionKind.CHOOSE, options=("A", "B"))
    alt = Alternative(id="ch", label="改候选",
                       material_override="甲 还是 乙？",
                       options_override=("甲", "乙"))
    r = asyncio.run(compare_alternatives(
        (baseline_sc, "原"), [alt], _personas(5), call))
    # baseline metric = share[A] ≈ 1; alt metric = share[A in baseline] = 0
    # 因为 alt 的输出全是 "甲"，不在 baseline 的 top
    assert r.baseline_metric > 0.9
    assert r.outcomes[0].metric == 0.0
