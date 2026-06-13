# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import pytest

from wanxiang.calibration import (FidelityReport, calibrate,
                                  calibrate_categorical, calibrate_numeric)
from wanxiang.simulation.aggregate import AggregateReport
from wanxiang.simulation.scenario import DecisionKind


# ---- 内部函数 ----

def test_categorical_perfect_match_gives_high_fidelity():
    sim = {"A": 0.5, "B": 0.3, "C": 0.2}
    truth = {"A": 0.5, "B": 0.3, "C": 0.2}
    r = calibrate_categorical(sim, truth)
    assert isinstance(r, FidelityReport)
    assert r.rmse == pytest.approx(0.0)
    assert r.euclidean == pytest.approx(0.0)
    assert r.fidelity_score == pytest.approx(1.0)
    assert r.spearman == pytest.approx(1.0)


def test_categorical_inverted_order_negative_spearman():
    sim = {"A": 0.6, "B": 0.3, "C": 0.1}
    truth = {"A": 0.1, "B": 0.3, "C": 0.6}
    r = calibrate_categorical(sim, truth)
    # 完全反序 -> spearman 接近 -1
    assert r.spearman < -0.9


def test_categorical_handles_missing_keys_with_notes():
    sim = {"A": 0.5, "B": 0.5}            # 没有 C
    truth = {"A": 0.5, "B": 0.3, "C": 0.2}
    r = calibrate_categorical(sim, truth)
    # 没崩；euclidean 非零；notes 提示
    assert r.euclidean > 0
    assert any("missing in sim" in n for n in r.notes)


def test_numeric_close_means_yields_high_fidelity():
    sim = {"mean": 5.0}
    truth = {"mean": 5.05}
    r = calibrate_numeric(sim, truth)
    assert r.rmse == pytest.approx(0.05)
    # 还做 mean 单点比较 -> spearman/euclidean 与 rmse 同源
    assert r.fidelity_score > 0.9


def test_numeric_missing_mean_raises():
    with pytest.raises(KeyError, match="mean"):
        calibrate_numeric({}, {"mean": 5})


# ---- 顶层 calibrate(report, truth) 路由 ----

def test_calibrate_routes_choose_to_categorical():
    rep = AggregateReport(
        kind=DecisionKind.CHOOSE, n_total=10, n_valid=10,
        error_count=0, error_rate=0.0,
        stats={"counts": {"A": 6, "B": 4}, "share": {"A": 0.6, "B": 0.4},
               "top": "A"})
    r = calibrate(rep, ground_truth={"A": 0.6, "B": 0.4})
    assert r.fidelity_score == pytest.approx(1.0)


def test_calibrate_routes_rate_to_numeric():
    rep = AggregateReport(
        kind=DecisionKind.RATE, n_total=5, n_valid=5,
        error_count=0, error_rate=0.0,
        stats={"mean": 6.0, "median": 6.0, "p25": 5, "p75": 7,
               "min": 5, "max": 7})
    r = calibrate(rep, ground_truth={"mean": 6.1})
    assert r.rmse == pytest.approx(0.1)


def test_calibrate_raises_on_empty_report():
    rep = AggregateReport(kind=None, n_total=0, n_valid=0,
                          error_count=0, error_rate=0.0, stats={})
    with pytest.raises(ValueError, match="empty"):
        calibrate(rep, ground_truth={"A": 1.0})


def test_calibrate_raises_when_no_valid_samples():
    rep = AggregateReport(kind=DecisionKind.RATE, n_total=3, n_valid=0,
                          error_count=3, error_rate=1.0, stats={})
    with pytest.raises(ValueError, match="no valid"):
        calibrate(rep, ground_truth={"mean": 5})


# ---- 边界 ----

def test_spearman_handles_ties():
    sim = {"A": 0.5, "B": 0.5}
    truth = {"A": 0.5, "B": 0.5}
    r = calibrate_categorical(sim, truth)
    # 全并列 + 完美匹配 -> spearman 应可计算且 = 1（或定义为 1，因为相同排序）
    assert r.spearman == pytest.approx(1.0)


def test_fidelity_score_clamped_to_zero_when_far_off():
    sim = {"A": 1.0, "B": 0.0}
    truth = {"A": 0.0, "B": 1.0}
    r = calibrate_categorical(sim, truth)
    # rmse = sqrt(((1-0)^2+(0-1)^2)/2) = 1.0 -> fidelity_score = 0.0
    assert r.fidelity_score == pytest.approx(0.0)
