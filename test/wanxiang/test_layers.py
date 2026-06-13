# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import pytest

from wanxiang.actions.layers import ActionLayer, SimulationMode


def test_action_layer_values():
    assert ActionLayer.L1_DECISION.value == 1
    assert ActionLayer.L2_SOCIAL.value == 2
    assert ActionLayer.L3_PLATFORM.value == 3


def test_mode_decision_only_includes_only_l1():
    mode = SimulationMode.DECISION_ONLY
    assert mode.active_layers() == [ActionLayer.L1_DECISION]


def test_mode_social_includes_l1_and_l2():
    mode = SimulationMode.SOCIAL
    assert mode.active_layers() == [ActionLayer.L1_DECISION, ActionLayer.L2_SOCIAL]


def test_mode_platform_includes_all_three():
    mode = SimulationMode.PLATFORM
    assert mode.active_layers() == [
        ActionLayer.L1_DECISION,
        ActionLayer.L2_SOCIAL,
        ActionLayer.L3_PLATFORM,
    ]


def test_platform_mode_requires_platform_name():
    assert SimulationMode.PLATFORM.requires_platform() is True
    assert SimulationMode.SOCIAL.requires_platform() is False
    assert SimulationMode.DECISION_ONLY.requires_platform() is False


def test_from_string_parses_canonical_names():
    assert SimulationMode.from_string("decision_only") is SimulationMode.DECISION_ONLY
    assert SimulationMode.from_string("social") is SimulationMode.SOCIAL
    assert SimulationMode.from_string("platform") is SimulationMode.PLATFORM


def test_from_string_rejects_unknown():
    with pytest.raises(ValueError, match="unknown simulation mode"):
        SimulationMode.from_string("l1_l3")
