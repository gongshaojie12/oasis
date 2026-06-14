# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""Bilingual report rendering (P3)."""
from __future__ import annotations

import pytest

from wanxiang.reporting.i18n import LABELS, label, kind_label
from wanxiang.reporting.report import build_report, render_markdown
from wanxiang.simulation.aggregate import AggregateReport
from wanxiang.simulation.scenario import DecisionKind, ScenarioConfig


def _agg():
    return AggregateReport(
        kind=DecisionKind.RATE,
        n_total=10, n_valid=10, error_count=0, error_rate=0.0,
        stats={"mean": 7.0, "median": 7.0, "stddev": 1.5,
               "p25": 6.0, "p75": 8.0, "min": 5.0, "max": 9.0},
    )


def _empty_agg():
    return AggregateReport(
        kind=DecisionKind.RATE,
        n_total=10, n_valid=0, error_count=10, error_rate=1.0,
        stats={},
    )


def _sc():
    return ScenarioConfig(material="m", question="q",
                          decision_kind=DecisionKind.RATE)


# ---- labels ----

def test_label_zh_by_default():
    assert "聚合" in label("section.aggregate")


def test_label_en_explicit():
    assert "Aggregate" in label("section.aggregate", locale="en")


def test_label_unknown_returns_key():
    assert label("does.not.exist", locale="en") == "does.not.exist"


def test_label_with_format_kwargs():
    out_en = label("title.subtitle_template", locale="en",
                   kind="Rate", n_valid=8, n_total=10)
    assert "Rate" in out_en and "8" in out_en


def test_all_labels_have_both_locales():
    for k, entry in LABELS.items():
        assert "zh" in entry, f"{k} missing zh"
        assert "en" in entry, f"{k} missing en"


def test_kind_label_known():
    assert "评分" in kind_label("rate", locale="zh")
    assert "Rate" in kind_label("rate", locale="en")


def test_kind_label_unknown_passthrough():
    assert kind_label("nonsense", locale="en") == "nonsense"


# ---- report ----

def test_build_report_default_locale_is_zh():
    r = build_report(scenario=_sc(), aggregate=_agg(), persona_count=10)
    assert r["locale"] == "zh"


def test_build_report_records_explicit_locale():
    r = build_report(scenario=_sc(), aggregate=_agg(), persona_count=10,
                     locale="en")
    assert r["locale"] == "en"


def test_render_markdown_zh_contains_chinese_headings():
    r = build_report(scenario=_sc(), aggregate=_agg(), persona_count=10,
                     locale="zh")
    md = render_markdown(r)
    assert "推荐" in md or "聚合" in md
    assert "万象" in md


def test_render_markdown_en_contains_english_headings():
    r = build_report(scenario=_sc(), aggregate=_agg(), persona_count=10,
                     locale="en")
    md = render_markdown(r)
    assert "WANXIANG" in md
    # En output should not include the core Chinese section headings
    assert "推荐结论" not in md
    assert "群体情绪演化" not in md


def test_render_markdown_en_disclaimer_in_english():
    r = build_report(scenario=_sc(), aggregate=_agg(), persona_count=10,
                     locale="en")
    md = render_markdown(r)
    assert ("probabilistic" in md.lower()
            or "forecast" in md.lower())


def test_render_markdown_locale_param_overrides_report_locale():
    r = build_report(scenario=_sc(), aggregate=_agg(), persona_count=10,
                     locale="zh")
    md = render_markdown(r, locale="en")
    assert "WANXIANG" in md


def test_render_markdown_no_valid_samples_en():
    r = build_report(scenario=_sc(), aggregate=_empty_agg(), persona_count=10,
                     locale="en")
    md = render_markdown(r)
    assert "No valid" in md


def test_render_markdown_no_valid_samples_zh():
    r = build_report(scenario=_sc(), aggregate=_empty_agg(), persona_count=10,
                     locale="zh")
    md = render_markdown(r)
    assert "无有效" in md


def test_render_markdown_legacy_caller_without_locale_still_chinese():
    """Pre-P3 callers that don't pass locale should keep getting Chinese."""
    r = build_report(scenario=_sc(), aggregate=_agg(), persona_count=10)
    md = render_markdown(r)
    assert "万象" in md
    # English heading words must not leak
    assert "Aggregate Results" not in md
