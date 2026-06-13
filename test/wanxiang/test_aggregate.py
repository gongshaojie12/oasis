# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import pytest

from wanxiang.simulation.aggregate import AggregateReport, aggregate
from wanxiang.simulation.decision import DecisionResult
from wanxiang.simulation.scenario import DecisionKind


def _rate(score, aid=0, err=None):
    return DecisionResult(agent_id=aid, kind=DecisionKind.RATE,
                          value=score, raw="", error=err)


def _choose(opt, aid=0, err=None):
    return DecisionResult(agent_id=aid, kind=DecisionKind.CHOOSE,
                          value=opt, raw="", error=err)


def test_aggregate_rate_returns_numeric_stats():
    results = [_rate(s, aid=i) for i, s in enumerate([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])]
    report = aggregate(results)
    assert isinstance(report, AggregateReport)
    assert report.kind is DecisionKind.RATE
    assert report.n_total == 10
    assert report.n_valid == 10
    assert report.error_count == 0
    s = report.stats
    assert s["mean"] == pytest.approx(5.5)
    assert s["median"] == pytest.approx(5.5)
    assert 2 <= s["p25"] <= 4
    assert 7 <= s["p75"] <= 9


def test_aggregate_choose_returns_counts_and_share():
    results = [_choose("A", 0), _choose("A", 1), _choose("B", 2),
               _choose("A", 3), _choose("C", 4)]
    report = aggregate(results)
    assert report.kind is DecisionKind.CHOOSE
    assert report.n_total == 5
    assert report.n_valid == 5
    counts = report.stats["counts"]
    share = report.stats["share"]
    assert counts == {"A": 3, "B": 1, "C": 1}
    assert share["A"] == pytest.approx(0.6)
    assert report.stats["top"] == "A"


def test_aggregate_excludes_errors_from_stats_but_counts_them():
    results = [_rate(5, 0), _rate(7, 1), _rate(None, 2, err="json bad"),
               _rate(None, 3, err="missing field")]
    report = aggregate(results)
    assert report.n_total == 4
    assert report.n_valid == 2
    assert report.error_count == 2
    assert report.error_rate == pytest.approx(0.5)
    assert report.stats["mean"] == pytest.approx(6.0)


def test_aggregate_empty_list_returns_empty_report():
    report = aggregate([])
    assert report.n_total == 0
    assert report.n_valid == 0
    assert report.error_count == 0
    assert report.stats == {}
    assert report.kind is None


def test_aggregate_all_errors_returns_empty_stats():
    results = [_rate(None, i, err="bad") for i in range(3)]
    report = aggregate(results)
    assert report.n_total == 3
    assert report.n_valid == 0
    assert report.error_count == 3
    assert report.error_rate == pytest.approx(1.0)
    assert report.stats == {}
    assert report.kind is DecisionKind.RATE


def test_aggregate_rejects_mixed_kinds():
    results = [_rate(5, 0), _choose("A", 1)]
    with pytest.raises(ValueError, match="mixed.*kind"):
        aggregate(results)
