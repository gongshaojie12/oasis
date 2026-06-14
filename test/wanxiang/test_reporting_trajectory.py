# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""M6+: 群体情绪演化曲线 — per-round mean/p25/p75."""
from __future__ import annotations

import pytest

from wanxiang.reporting.trajectory import TrajectoryPoint, build_trajectory
from wanxiang.simulation.decision import DecisionResult
from wanxiang.simulation.scenario import DecisionKind


def _r(agent_id, value, kind=DecisionKind.RATE):
    return DecisionResult(agent_id=agent_id, kind=kind, value=value,
                          raw=f'{{"score": {value}}}', error=None)


def test_build_trajectory_one_point_per_round():
    rounds = [
        [_r(1, 3), _r(2, 5)],
        [_r(1, 5), _r(2, 7)],
        [_r(1, 6), _r(2, 8)],
    ]
    traj = build_trajectory(rounds, "rate")
    assert len(traj) == 3
    assert [p.round_idx for p in traj] == [0, 1, 2]


def test_mean_increases_with_drift():
    rounds = [
        [_r(1, 3), _r(2, 5)],
        [_r(1, 5), _r(2, 7)],
        [_r(1, 6), _r(2, 8)],
    ]
    traj = build_trajectory(rounds, "rate")
    means = [p.mean for p in traj]
    assert means[0] == pytest.approx(4.0)
    assert means[1] == pytest.approx(6.0)
    assert means[2] == pytest.approx(7.0)


def test_quartiles_reflect_iqr():
    # Need ≥4 points for meaningful quartiles
    rounds = [
        [_r(1, 1), _r(2, 3), _r(3, 7), _r(4, 9)],
    ]
    traj = build_trajectory(rounds, "rate")
    p = traj[0]
    assert p.n_valid == 4
    # statistics.quantiles exclusive method on [1,3,7,9]
    # gives p25=1.5, median=5, p75=8.5
    assert p.p25 < p.p75
    assert p.p25 == pytest.approx(1.5)
    assert p.p75 == pytest.approx(8.5)


def test_empty_round_has_no_stats():
    rounds = [
        [],
        [_r(1, 5)],
    ]
    traj = build_trajectory(rounds, "rate")
    assert traj[0].n_valid == 0
    assert traj[0].mean is None
    assert traj[0].p25 is None
    assert traj[0].p75 is None
    assert traj[1].n_valid == 1
    assert traj[1].mean == pytest.approx(5.0)


def test_non_numeric_kind_raises():
    with pytest.raises(ValueError):
        build_trajectory([[DecisionResult(
            agent_id=1, kind=DecisionKind.CHOOSE, value="A",
            raw='{"option":"A"}', error=None)]], "choose")


def test_single_round_returns_one_element():
    rounds = [[_r(1, 4), _r(2, 6)]]
    traj = build_trajectory(rounds, "rate")
    assert len(traj) == 1
    assert traj[0].round_idx == 0
    assert traj[0].mean == pytest.approx(5.0)


def test_errored_results_skipped_in_stats():
    rounds = [[
        _r(1, 5),
        DecisionResult(agent_id=2, kind=DecisionKind.RATE, value=None,
                        raw="x", error="bad json"),
        _r(3, 7),
    ]]
    traj = build_trajectory(rounds, "rate")
    assert traj[0].n_valid == 2
    assert traj[0].mean == pytest.approx(6.0)
