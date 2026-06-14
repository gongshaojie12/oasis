# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""build_report + render_markdown 支持 causal/counterfactual。"""
import pytest

from wanxiang.reasoning.causal import CausalReport, FactorContribution
from wanxiang.reasoning.counterfactual import (AlternativeOutcome,
                                                  CounterfactualReport)
from wanxiang.reporting import build_report, render_markdown
from wanxiang.simulation.aggregate import AggregateReport
from wanxiang.simulation.scenario import DecisionKind, ScenarioConfig


def _agg():
    return AggregateReport(
        kind=DecisionKind.RATE, n_total=10, n_valid=10,
        error_count=0, error_rate=0.0,
        stats={"mean": 6.0, "median": 6, "p25": 5, "p75": 7,
               "min": 1, "max": 10})


def _sc():
    return ScenarioConfig(material="m", question="q",
                          decision_kind=DecisionKind.RATE)


def _causal():
    return CausalReport(
        baseline_metric=6.0,
        contributions=[
            FactorContribution(factor_id="health",
                                factor_label="0糖0卡 卖点",
                                baseline_metric=6.0, ablated_metric=3.5,
                                delta=2.5, abs_delta=2.5, rank=1),
            FactorContribution(factor_id="channel",
                                factor_label="小红书 渠道",
                                baseline_metric=6.0, ablated_metric=5.0,
                                delta=1.0, abs_delta=1.0, rank=2),
        ],
        notes=[])


def _cf():
    return CounterfactualReport(
        baseline_label="原价 ¥6",
        baseline_metric=6.0,
        outcomes=[
            AlternativeOutcome(alt_id="cheap", label="降到 ¥5",
                                metric=6.5, delta_vs_baseline=0.5),
            AlternativeOutcome(alt_id="pricey", label="涨到 ¥10",
                                metric=3.5, delta_vs_baseline=-2.5),
        ])


def test_build_report_attaches_causal_when_passed():
    rep = build_report(scenario=_sc(), aggregate=_agg(),
                       persona_count=10, causal=_causal())
    assert rep["causal"] is not None
    assert rep["causal"]["contributions"][0]["factor_id"] == "health"


def test_build_report_attaches_counterfactual_when_passed():
    rep = build_report(scenario=_sc(), aggregate=_agg(),
                       persona_count=10, counterfactual=_cf())
    assert rep["counterfactual"]["baseline_label"] == "原价 ¥6"
    assert len(rep["counterfactual"]["outcomes"]) == 2


def test_build_report_without_extras_works_as_before():
    rep = build_report(scenario=_sc(), aggregate=_agg(), persona_count=10)
    assert rep.get("causal") is None
    assert rep.get("counterfactual") is None


def test_render_markdown_includes_causal_section():
    rep = build_report(scenario=_sc(), aggregate=_agg(),
                       persona_count=10, causal=_causal())
    md = render_markdown(rep)
    assert "因果归因" in md
    assert "0糖0卡" in md
    assert "2.5" in md or "2.50" in md  # delta 出现


def test_render_markdown_includes_counterfactual_section():
    rep = build_report(scenario=_sc(), aggregate=_agg(),
                       persona_count=10, counterfactual=_cf())
    md = render_markdown(rep)
    assert "反事实" in md or "对照" in md
    assert "降到 ¥5" in md
    assert "涨到 ¥10" in md
