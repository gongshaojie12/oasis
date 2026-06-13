# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import pytest

from wanxiang.calibration.fidelity import FidelityReport
from wanxiang.reporting import (build_report,
                                 render_markdown)
from wanxiang.simulation.aggregate import AggregateReport
from wanxiang.simulation.scenario import DecisionKind, ScenarioConfig


def _choose_report():
    return AggregateReport(
        kind=DecisionKind.CHOOSE, n_total=1000, n_valid=995,
        error_count=5, error_rate=0.005,
        stats={"counts": {"青提": 600, "白桃": 250, "海盐荔枝": 145},
               "share": {"青提": 0.603, "白桃": 0.251, "海盐荔枝": 0.146},
               "top": "青提"})


def _rate_report():
    return AggregateReport(
        kind=DecisionKind.RATE, n_total=500, n_valid=500,
        error_count=0, error_rate=0.0,
        stats={"mean": 6.8, "median": 7, "p25": 5, "p75": 8,
               "min": 1, "max": 10})


def _scenario_choose():
    return ScenarioConfig(
        material="新品口味测试", question="你最想买哪个？",
        decision_kind=DecisionKind.CHOOSE,
        options=("青提", "白桃", "海盐荔枝"))


def _scenario_rate():
    return ScenarioConfig(
        material="¥6 定价", question="0-10 购买意愿评分",
        decision_kind=DecisionKind.RATE)


def _fid_high():
    return FidelityReport(spearman=0.92, rmse=0.04, euclidean=0.06,
                          fidelity_score=0.96, notes=[])


# ---- build_report 结构化输出 ----

def test_build_report_choose_includes_recommendation_and_share():
    rep = build_report(scenario=_scenario_choose(),
                       aggregate=_choose_report(),
                       persona_count=1000)
    assert rep["recommendation"]["top"] == "青提"
    assert rep["recommendation"]["share"] == pytest.approx(0.603)
    assert rep["n_total"] == 1000
    assert rep["n_valid"] == 995
    assert rep["error_count"] == 5
    # 排序后的份额列表（chat.html 工件卡用）
    breakdown = rep["breakdown"]
    assert breakdown[0]["option"] == "青提"
    assert breakdown[0]["share"] == pytest.approx(0.603)
    assert breakdown[-1]["option"] == "海盐荔枝"
    # 默认无校准
    assert rep["fidelity"] is None


def test_build_report_rate_includes_mean_and_percentile_band():
    rep = build_report(scenario=_scenario_rate(),
                       aggregate=_rate_report(),
                       persona_count=500)
    assert rep["recommendation"]["mean"] == pytest.approx(6.8)
    assert rep["recommendation"]["confidence_band"] == pytest.approx((5.0, 8.0))
    assert rep["n_valid"] == 500


def test_build_report_attaches_fidelity_when_provided():
    rep = build_report(scenario=_scenario_choose(),
                       aggregate=_choose_report(),
                       persona_count=1000,
                       fidelity=_fid_high())
    fid = rep["fidelity"]
    assert fid["score"] == pytest.approx(0.96)
    assert fid["spearman"] == pytest.approx(0.92)
    assert fid["label"] in {"高", "中", "低"}


def test_build_report_classifies_fidelity_label():
    high = FidelityReport(0.9, 0.04, 0.06, 0.95, [])
    mid = FidelityReport(0.6, 0.18, 0.2, 0.78, [])
    low = FidelityReport(0.2, 0.45, 0.5, 0.40, [])
    for fid, expected in [(high, "高"), (mid, "中"), (low, "低")]:
        rep = build_report(scenario=_scenario_choose(),
                           aggregate=_choose_report(),
                           persona_count=10, fidelity=fid)
        assert rep["fidelity"]["label"] == expected


def test_build_report_rejects_empty_aggregate():
    empty = AggregateReport(kind=None, n_total=0, n_valid=0,
                            error_count=0, error_rate=0.0, stats={})
    with pytest.raises(ValueError, match="empty"):
        build_report(scenario=_scenario_choose(), aggregate=empty,
                     persona_count=0)


# ---- render_markdown 文本 ----

def test_render_markdown_includes_key_sections():
    rep = build_report(scenario=_scenario_choose(),
                       aggregate=_choose_report(),
                       persona_count=1000,
                       fidelity=_fid_high())
    md = render_markdown(rep)
    assert isinstance(md, str)
    # 标题、推荐、占比、保真度都要出现
    assert "# " in md  # 顶级标题
    assert "推荐" in md or "Recommendation" in md
    assert "青提" in md
    assert "60" in md  # 60% 占比
    assert "保真度" in md
    # 含警告（出错样本）
    assert "5" in md  # error_count=5


def test_render_markdown_rate_includes_mean_and_band():
    rep = build_report(scenario=_scenario_rate(),
                       aggregate=_rate_report(),
                       persona_count=500)
    md = render_markdown(rep)
    assert "6.8" in md or "6.80" in md
    assert "5" in md and "8" in md  # 置信带


def test_render_markdown_without_fidelity_omits_section():
    rep = build_report(scenario=_scenario_choose(),
                       aggregate=_choose_report(),
                       persona_count=1000)
    md = render_markdown(rep)
    assert "保真度" not in md


# ---- zero-valid sample 容错（Bug 修复 TDD）----

def _empty_rate_report():
    return AggregateReport(kind=DecisionKind.RATE, n_total=10, n_valid=0,
                            error_count=10, error_rate=1.0, stats={})


def _empty_choose_report():
    return AggregateReport(kind=DecisionKind.CHOOSE, n_total=10, n_valid=0,
                            error_count=10, error_rate=1.0, stats={})


def _scenario_rate_simple():
    return ScenarioConfig(material="m", question="q",
                          decision_kind=DecisionKind.RATE)


def _scenario_choose_simple():
    return ScenarioConfig(material="m", question="q",
                          decision_kind=DecisionKind.CHOOSE,
                          options=("A", "B"))


def test_build_report_handles_zero_valid_samples_rate():
    rep = build_report(scenario=_scenario_rate_simple(),
                       aggregate=_empty_rate_report(),
                       persona_count=10)
    # 不抛；标记 no_valid
    assert rep["n_valid"] == 0
    assert rep.get("no_valid_samples") is True


def test_build_report_handles_zero_valid_samples_choose():
    rep = build_report(scenario=_scenario_choose_simple(),
                       aggregate=_empty_choose_report(),
                       persona_count=10)
    assert rep["n_valid"] == 0
    assert rep.get("no_valid_samples") is True


def test_render_markdown_zero_valid_rate_does_not_crash():
    rep = build_report(scenario=_scenario_rate_simple(),
                       aggregate=_empty_rate_report(),
                       persona_count=10)
    md = render_markdown(rep)
    assert isinstance(md, str)
    # 应明确告知无有效样本
    assert "无有效样本" in md or "0 / 10" in md


def test_render_markdown_zero_valid_choose_does_not_crash():
    rep = build_report(scenario=_scenario_choose_simple(),
                       aggregate=_empty_choose_report(),
                       persona_count=10)
    md = render_markdown(rep)
    assert isinstance(md, str)
    assert "无有效样本" in md or "0 / 10" in md
