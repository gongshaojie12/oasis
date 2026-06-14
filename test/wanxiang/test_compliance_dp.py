# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""Laplace noise + DP application."""
import math
import random
import pytest

from wanxiang.compliance.dp import laplace_noise, apply_dp_to_aggregate


def test_laplace_noise_deterministic_with_seed():
    n1 = laplace_noise(1.0, rng=random.Random(42))
    n2 = laplace_noise(1.0, rng=random.Random(42))
    assert n1 == n2


def test_laplace_noise_mean_near_zero_large_n():
    rng = random.Random(0)
    samples = [laplace_noise(1.0, rng=rng) for _ in range(5000)]
    assert abs(sum(samples)/len(samples)) < 0.1  # within 0.1 of 0


def test_apply_dp_perturbs_mean():
    agg = {"mean": 5.0, "quartiles": {"p25": 4.0, "p50": 5.0, "p75": 6.0}, "n": 100}
    out = apply_dp_to_aggregate(agg, epsilon=1.0, rng=random.Random(42))
    # mean changed
    assert out["mean"] != 5.0
    # other fields preserved
    assert out["n"] == 100


def test_apply_dp_perturbs_quartiles():
    agg = {"mean": 5.0, "quartiles": {"p25": 4.0, "p50": 5.0, "p75": 6.0}}
    out = apply_dp_to_aggregate(agg, epsilon=1.0, rng=random.Random(42))
    assert out["quartiles"]["p25"] != 4.0
    assert out["quartiles"]["p50"] != 5.0


def test_apply_dp_skips_none_fields():
    agg = {"mean": None, "quartiles": {"p25": None, "p50": 5.0, "p75": None}}
    out = apply_dp_to_aggregate(agg, epsilon=1.0, rng=random.Random(0))
    assert out["mean"] is None
    assert out["quartiles"]["p25"] is None


def test_apply_dp_smaller_epsilon_larger_noise():
    rng1 = random.Random(0)
    rng2 = random.Random(0)
    agg = {"mean": 5.0, "quartiles": {}}
    out_loose = apply_dp_to_aggregate(agg, epsilon=10.0, rng=rng1)
    out_tight = apply_dp_to_aggregate(agg, epsilon=0.1, rng=rng2)
    # Smaller epsilon → larger noise magnitude (same uniform draw)
    assert abs(out_tight["mean"] - 5.0) > abs(out_loose["mean"] - 5.0)


def test_apply_dp_zero_epsilon_raises():
    with pytest.raises(ValueError):
        apply_dp_to_aggregate({"mean": 1.0, "quartiles": {}}, epsilon=0.0)


def test_apply_dp_negative_epsilon_raises():
    with pytest.raises(ValueError):
        apply_dp_to_aggregate({"mean": 1.0, "quartiles": {}}, epsilon=-1.0)


def test_apply_dp_does_not_mutate_input():
    agg = {"mean": 5.0, "quartiles": {"p50": 5.0}}
    apply_dp_to_aggregate(agg, epsilon=1.0)
    assert agg["mean"] == 5.0
    assert agg["quartiles"]["p50"] == 5.0
