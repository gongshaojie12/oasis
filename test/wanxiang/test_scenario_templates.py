# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""Scenario template loader + instantiate logic."""
import os

import pytest

from wanxiang.scenarios import (ScenarioTemplate, instantiate,
                                  list_templates, load_template)
from wanxiang.simulation.scenario import DecisionKind


def test_load_consumer_concept_test_template():
    t = load_template("consumer_concept_test")
    assert isinstance(t, ScenarioTemplate)
    assert t.id == "consumer_concept_test"
    assert t.decision_kind is DecisionKind.CHOOSE
    assert t.default_options  # 应该自带候选


def test_load_marketing_ad_template():
    t = load_template("marketing_ad_ab_test")
    assert t.decision_kind is DecisionKind.RATE


def test_load_brand_sentiment_template():
    t = load_template("brand_sentiment_probe")
    assert t.decision_kind is DecisionKind.SENTIMENT


def test_load_missing_template_raises():
    with pytest.raises(FileNotFoundError):
        load_template("nonexistent_template_xxx")


def test_list_templates_includes_all_three():
    ts = list_templates()
    ids = {t.id for t in ts}
    assert "consumer_concept_test" in ids
    assert "marketing_ad_ab_test" in ids
    assert "brand_sentiment_probe" in ids


def test_instantiate_fills_material_and_question():
    t = load_template("marketing_ad_ab_test")
    var_names = [v["name"] for v in t.variables]
    values = {n: f"<{n}>" for n in var_names}
    out = instantiate(t, values)
    assert out["kind"] == "rate"
    # 模板的 {var} 都被替换
    for n in var_names:
        assert f"<{n}>" in out["material"] or f"<{n}>" in out["question"]


def test_instantiate_choose_uses_default_options():
    t = load_template("consumer_concept_test")
    var_names = [v["name"] for v in t.variables]
    values = {n: "x" for n in var_names}
    out = instantiate(t, values)
    assert out["kind"] == "choose"
    assert out["options"] == list(t.default_options)


def test_instantiate_choose_with_override_options():
    t = load_template("consumer_concept_test")
    var_names = [v["name"] for v in t.variables]
    values = {n: "x" for n in var_names}
    out = instantiate(t, values, options=["甲", "乙", "丙"])
    assert out["options"] == ["甲", "乙", "丙"]


def test_instantiate_missing_required_variable_raises():
    t = load_template("marketing_ad_ab_test")
    # 不传任何 values → 必填字段缺失
    with pytest.raises(ValueError, match="required"):
        instantiate(t, {})


def test_instantiate_default_value_used_when_missing():
    """变量有 default 且不必填，可省略。"""
    t = load_template("brand_sentiment_probe")
    has_default = [v for v in t.variables if v.get("default") is not None]
    if not has_default:
        pytest.skip("template has no defaultable variables")
    # 填必填的；省略 has_default 中第一个
    skip = has_default[0]["name"]
    values = {v["name"]: "x" for v in t.variables
              if v["name"] != skip and v.get("required", False)}
    out = instantiate(t, values)
    # 不抛 → 通过
    assert out["kind"] == "sentiment"
