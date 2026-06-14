# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""M6+: build_report / render_markdown integrate rejection, trajectory, commentary."""
from __future__ import annotations

import pytest

from wanxiang.reporting import build_report, render_markdown
from wanxiang.simulation.aggregate import AggregateReport
from wanxiang.simulation.scenario import DecisionKind, ScenarioConfig


def _agg_rate():
    return AggregateReport(
        kind=DecisionKind.RATE, n_total=10, n_valid=10,
        error_count=0, error_rate=0.0,
        stats={"mean": 6.0, "median": 6, "p25": 5, "p75": 7,
               "min": 1, "max": 10})


def _sc():
    return ScenarioConfig(material="材料", question="问题",
                          decision_kind=DecisionKind.RATE)


def test_build_report_accepts_rejection_analysis():
    rej = {"total_rejected": 3,
           "buckets": {"price_too_high": 2, "no_need": 1},
           "examples": {"price_too_high": ["太贵"], "no_need": ["不需要"]}}
    rep = build_report(scenario=_sc(), aggregate=_agg_rate(),
                       persona_count=10, rejection_analysis=rej)
    assert rep["rejection_analysis"] is not None
    assert rep["rejection_analysis"]["total_rejected"] == 3


def test_render_markdown_includes_rejection_section():
    rej = {"total_rejected": 3,
           "buckets": {"price_too_high": 2, "no_need": 1},
           "examples": {"price_too_high": ["太贵了"]}}
    rep = build_report(scenario=_sc(), aggregate=_agg_rate(),
                       persona_count=10, rejection_analysis=rej)
    md = render_markdown(rep)
    assert "## 劝退原因构成" in md
    assert "price_too_high" in md or "价格" in md


def test_render_markdown_includes_trajectory_when_multiple_points():
    traj = [
        {"round_idx": 0, "n_valid": 10, "mean": 4.0, "p25": 3.0, "p75": 5.0},
        {"round_idx": 1, "n_valid": 10, "mean": 5.5, "p25": 4.0, "p75": 7.0},
        {"round_idx": 2, "n_valid": 10, "mean": 6.5, "p25": 5.0, "p75": 8.0},
    ]
    rep = build_report(scenario=_sc(), aggregate=_agg_rate(),
                       persona_count=10, trajectory=traj)
    md = render_markdown(rep)
    assert "## 群体情绪演化" in md
    assert "round" in md.lower() or "轮次" in md or "round_idx" in md.lower()


def test_render_markdown_omits_trajectory_with_one_point():
    traj = [{"round_idx": 0, "n_valid": 10, "mean": 4.0,
              "p25": 3.0, "p75": 5.0}]
    rep = build_report(scenario=_sc(), aggregate=_agg_rate(),
                       persona_count=10, trajectory=traj)
    md = render_markdown(rep)
    assert "## 群体情绪演化" not in md


def test_render_markdown_includes_commentary_section():
    rep = build_report(scenario=_sc(), aggregate=_agg_rate(),
                       persona_count=10,
                       commentary="群体整体偏正面，价格阻力明显。")
    md = render_markdown(rep)
    assert "## LLM 解读" in md
    assert "群体整体偏正面" in md


def test_old_report_still_renders_without_new_kwargs():
    rep = build_report(scenario=_sc(), aggregate=_agg_rate(),
                       persona_count=10)
    md = render_markdown(rep)
    assert "# 万象模拟报告" in md
    assert "## 推荐结论" in md
    assert "## 劝退原因构成" not in md
    assert "## 群体情绪演化" not in md
    assert "## LLM 解读" not in md
