# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""M6+: 劝退原因构成 — bucket DecisionResult reasoning into categories."""
from __future__ import annotations

import pytest

from wanxiang.reporting.rejection import (
    DEFAULT_BUCKET, REJECTION_BUCKETS, analyze_rejection_reasons,
    bucket_reason)
from wanxiang.simulation.decision import DecisionResult
from wanxiang.simulation.scenario import DecisionKind


def _r(agent_id, value, reasoning, kind=DecisionKind.RATE, error=None):
    """Build a DecisionResult with reasoning packed into raw JSON."""
    import json
    raw = json.dumps({"score": value, "reasoning": reasoning},
                      ensure_ascii=False)
    return DecisionResult(agent_id=agent_id, kind=kind, value=value,
                          raw=raw, error=error)


# ---- bucket_reason ----

def test_bucket_reason_matches_price_too_high_cn():
    assert bucket_reason("太贵了买不起") == "price_too_high"


def test_bucket_reason_matches_price_too_high_en_case_insensitive():
    assert bucket_reason("Way too EXPENSIVE for me") == "price_too_high"


def test_bucket_reason_matches_low_quality():
    assert bucket_reason("感觉是假货质量差") == "low_quality_concern"


def test_bucket_reason_matches_no_need():
    assert bucket_reason("我真的不需要这个") == "no_need"


def test_bucket_reason_matches_brand_distrust():
    assert bucket_reason("没听过这个山寨牌子") == "brand_distrust"


def test_bucket_reason_matches_competitor():
    assert bucket_reason("我已经有更好的替代品") == "competitor_preferred"


def test_bucket_reason_matches_uncertainty():
    assert bucket_reason("再看看吧不确定") == "uncertainty"


def test_bucket_reason_returns_default_for_unmatched():
    assert bucket_reason("纯粹的随机文字 random stuff") == DEFAULT_BUCKET


def test_bucket_reason_handles_empty():
    assert bucket_reason("") == DEFAULT_BUCKET


def test_buckets_dict_has_expected_categories():
    assert "price_too_high" in REJECTION_BUCKETS
    assert "low_quality_concern" in REJECTION_BUCKETS
    assert "no_need" in REJECTION_BUCKETS
    assert "brand_distrust" in REJECTION_BUCKETS
    assert "competitor_preferred" in REJECTION_BUCKETS
    assert "uncertainty" in REJECTION_BUCKETS


# ---- analyze_rejection_reasons (numeric kinds) ----

def test_analyze_rate_default_threshold_5():
    results = [
        _r(1, 3, "太贵"),
        _r(2, 8, "非常好"),
        _r(3, 2, "没必要"),
        _r(4, 4, "质量差"),
        _r(5, 9, "棒"),
    ]
    out = analyze_rejection_reasons(results, "rate")
    assert out["total_rejected"] == 3
    assert out["buckets"]["price_too_high"] == 1
    assert out["buckets"]["no_need"] == 1
    assert out["buckets"]["low_quality_concern"] == 1


def test_analyze_rate_custom_threshold():
    results = [
        _r(1, 3, "太贵"),
        _r(2, 6, "凑合 unnecessary"),  # 6 is below threshold 7, "no_need"
        _r(3, 9, "great"),
    ]
    out = analyze_rejection_reasons(results, "rate", threshold=7)
    assert out["total_rejected"] == 2


def test_analyze_sentiment_default_threshold_zero():
    results = [
        DecisionResult(agent_id=1, kind=DecisionKind.SENTIMENT, value=-0.5,
                        raw='{"polarity": -0.5, "reasoning": "太贵"}',
                        error=None),
        DecisionResult(agent_id=2, kind=DecisionKind.SENTIMENT, value=0.7,
                        raw='{"polarity": 0.7, "reasoning": "great"}',
                        error=None),
        DecisionResult(agent_id=3, kind=DecisionKind.SENTIMENT, value=-0.1,
                        raw='{"polarity": -0.1, "reasoning": "再看看"}',
                        error=None),
    ]
    out = analyze_rejection_reasons(results, "sentiment")
    assert out["total_rejected"] == 2
    assert out["buckets"]["price_too_high"] == 1
    assert out["buckets"]["uncertainty"] == 1


def test_analyze_click_probability_default_threshold_half():
    results = [
        DecisionResult(agent_id=1, kind=DecisionKind.CLICK_PROBABILITY,
                        value=0.3,
                        raw='{"probability": 0.3, "reasoning": "太贵"}',
                        error=None),
        DecisionResult(agent_id=2, kind=DecisionKind.CLICK_PROBABILITY,
                        value=0.9,
                        raw='{"probability": 0.9, "reasoning": "good"}',
                        error=None),
    ]
    out = analyze_rejection_reasons(results, "click_probability")
    assert out["total_rejected"] == 1
    assert out["buckets"]["price_too_high"] == 1


# ---- analyze_rejection_reasons (choose) ----

def test_analyze_choose_buckets_non_winners():
    results = [
        DecisionResult(agent_id=1, kind=DecisionKind.CHOOSE, value="青提",
                        raw='{"option": "青提", "reasoning": "好吃"}',
                        error=None),
        DecisionResult(agent_id=2, kind=DecisionKind.CHOOSE, value="白桃",
                        raw='{"option": "白桃", "reasoning": "青提太贵"}',
                        error=None),
        DecisionResult(agent_id=3, kind=DecisionKind.CHOOSE, value="荔枝",
                        raw='{"option": "荔枝", "reasoning": "青提不需要"}',
                        error=None),
    ]
    out = analyze_rejection_reasons(results, "choose", threshold="青提")
    assert out["total_rejected"] == 2  # 2 didn't pick 青提
    assert out["buckets"]["price_too_high"] == 1
    assert out["buckets"]["no_need"] == 1


# ---- shape and edge cases ----

def test_buckets_sorted_descending_by_count():
    results = [
        _r(1, 2, "太贵"),
        _r(2, 2, "太贵"),
        _r(3, 2, "太贵"),
        _r(4, 2, "质量差"),
        _r(5, 2, "不需要"),
    ]
    out = analyze_rejection_reasons(results, "rate")
    keys = list(out["buckets"].keys())
    assert keys[0] == "price_too_high"
    assert out["buckets"][keys[0]] >= out["buckets"][keys[1]]
    assert out["buckets"][keys[1]] >= out["buckets"][keys[2]]


def test_examples_capped_at_two_per_bucket():
    results = [
        _r(1, 2, "太贵 reason 1"),
        _r(2, 2, "太贵 reason 2"),
        _r(3, 2, "太贵 reason 3"),
        _r(4, 2, "太贵 reason 4"),
    ]
    out = analyze_rejection_reasons(results, "rate")
    assert out["buckets"]["price_too_high"] == 4
    assert len(out["examples"]["price_too_high"]) == 2


def test_skips_errored_results():
    results = [
        _r(1, 3, "太贵"),
        DecisionResult(agent_id=2, kind=DecisionKind.RATE, value=None,
                        raw="garbage", error="invalid json: ..."),
        _r(3, 2, "质量差"),
    ]
    out = analyze_rejection_reasons(results, "rate")
    assert out["total_rejected"] == 2


def test_skips_empty_reasoning():
    results = [
        _r(1, 3, ""),       # empty reasoning
        _r(2, 2, "太贵"),
    ]
    out = analyze_rejection_reasons(results, "rate")
    # Empty reasoning still counts as "rejected" but lands in default bucket;
    # spec says "Skip results with error or empty reasoning"
    assert out["total_rejected"] == 1


def test_empty_input_returns_zero():
    out = analyze_rejection_reasons([], "rate")
    assert out["total_rejected"] == 0
    assert out["buckets"] == {}
    assert out["examples"] == {}
