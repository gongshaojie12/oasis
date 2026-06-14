# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""Pure expand_grid + combo_id + apply_combo logic."""
import pytest

from wanxiang.api.sweep import expand_grid, combo_id, apply_combo
from wanxiang.api.schemas import SimulateRequest, ScenarioPayload, ModelConfig


def _req(material="给你看一条广告：{copy}", question="买不买？", **k):
    return SimulateRequest(
        distribution_path="/x.yaml", n=10, seed=1,
        scenario=ScenarioPayload(material=material, question=question, kind="rate"),
        rounds=0, model=ModelConfig(provider="stub"), **k)


def test_expand_empty_grid_returns_single_empty_combo():
    assert expand_grid({}) == [{}]


def test_expand_single_axis():
    r = expand_grid({"copy": ["A", "B", "C"]})
    assert len(r) == 3
    assert {"copy": "A"} in r


def test_expand_two_axes_product():
    r = expand_grid({"copy": ["A", "B"], "channel": ["x", "y"]})
    assert len(r) == 4
    assert {"copy": "A", "channel": "x"} in r
    assert {"copy": "B", "channel": "y"} in r


def test_expand_three_axes_count():
    r = expand_grid({"a": ["1", "2"], "b": ["x", "y", "z"], "c": ["P", "Q"]})
    assert len(r) == 12


def test_combo_id_is_stable_and_sorted():
    cid = combo_id({"channel": "xhs", "copy": "A"})
    # sorted by key alphabetically
    assert cid == "channel=xhs|copy=A"


def test_combo_id_empty_values():
    assert combo_id({}) == ""


def test_apply_combo_substitutes_in_material():
    req = _req(material="广告：{copy}")
    new = apply_combo(req, {"copy": "打 9 折"})
    assert new.scenario.material == "广告：打 9 折"
    # original is unchanged
    assert req.scenario.material == "广告：{copy}"


def test_apply_combo_substitutes_in_question():
    req = _req(material="x", question="在{channel}上看到这条广告，你会买吗？")
    new = apply_combo(req, {"channel": "小红书"})
    assert "小红书" in new.scenario.question


def test_apply_combo_missing_key_left_verbatim():
    req = _req(material="{copy} on {channel}")
    new = apply_combo(req, {"copy": "A"})
    # {channel} stays as literal
    assert new.scenario.material == "A on {channel}"


def test_apply_combo_no_placeholders_is_noop():
    req = _req(material="literal text", question="?")
    new = apply_combo(req, {"copy": "A"})
    assert new.scenario.material == "literal text"
