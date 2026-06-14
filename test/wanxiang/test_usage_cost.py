# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""Cost calculation rules."""
import pytest

from wanxiang.api.usage import compute_cost_units, derive_mode_label


def test_decision_only_cost_is_n():
    assert compute_cost_units("decision_only", n_agents=100, rounds=0) == 100


def test_social_cost_scales_with_rounds():
    # n=10, rounds=2 → 10 * (2+1) = 30
    assert compute_cost_units("social", n_agents=10, rounds=2) == 30


def test_platform_cost_has_1_5x_multiplier():
    # n=10, rounds=2 → 10 * 3 * 1.5 = 45
    assert compute_cost_units("platform", n_agents=10, rounds=2) == 45


def test_platform_cost_rounds_up():
    # n=3, rounds=1 → 3 * 2 * 1.5 = 9.0 → 9
    # n=3, rounds=2 → 3 * 3 * 1.5 = 13.5 → 14
    assert compute_cost_units("platform", n_agents=3, rounds=2) == 14


def test_unknown_mode_raises():
    with pytest.raises(ValueError, match="unknown mode"):
        compute_cost_units("nonsense", 10, 0)


def test_derive_mode_label_decision_only():
    assert derive_mode_label(rounds=0, platform=None) == "decision_only"
    assert derive_mode_label(rounds=0, platform="wechat") == "decision_only"  # platform ignored


def test_derive_mode_label_social():
    assert derive_mode_label(rounds=1, platform=None) == "social"
    assert derive_mode_label(rounds=5, platform=None) == "social"


def test_derive_mode_label_platform():
    assert derive_mode_label(rounds=1, platform="wechat") == "platform"
    assert derive_mode_label(rounds=2, platform="douyin") == "platform"
