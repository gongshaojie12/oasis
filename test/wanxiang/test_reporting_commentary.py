# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""M6+: LLM 自然语言解读 — feed report dict to model_call, get CN summary."""
from __future__ import annotations

import asyncio

import pytest

from wanxiang.reporting.commentary import generate_commentary


def _make_fake_call(reply: str = "群体整体偏正面，受品牌信任度驱动..."):
    captured = {"messages": None}

    async def call(messages):
        captured["messages"] = messages
        return reply

    return call, captured


def _base_report():
    return {
        "scenario": {"decision_kind": "rate",
                      "question": "0-10 购买意愿评分",
                      "material": "新品 0糖 ¥6"},
        "persona_count": 100,
        "n_total": 100, "n_valid": 95, "error_count": 5, "error_rate": 0.05,
        "recommendation": {"mean": 6.8,
                           "confidence_band": (5.0, 8.0),
                           "range": (1, 10)},
        "breakdown": [],
        "fidelity": None,
        "causal": None,
        "counterfactual": None,
    }


def test_generate_commentary_calls_model_with_messages():
    call, captured = _make_fake_call()
    result = asyncio.run(generate_commentary(_base_report(), call))
    assert captured["messages"] is not None
    assert isinstance(captured["messages"], list)
    assert len(captured["messages"]) >= 1
    for m in captured["messages"]:
        assert "role" in m and "content" in m


def test_prompt_mentions_kind_mean_and_n():
    call, captured = _make_fake_call()
    asyncio.run(generate_commentary(_base_report(), call))
    content = "\n".join(m["content"] for m in captured["messages"])
    assert "rate" in content or "评分" in content
    assert "6.8" in content
    assert "95" in content


def test_prompt_mentions_rejection_when_present():
    rep = _base_report()
    rep["rejection_analysis"] = {
        "total_rejected": 30,
        "buckets": {"price_too_high": 15, "no_need": 10, "uncertainty": 5},
        "examples": {"price_too_high": ["太贵了"]},
    }
    call, captured = _make_fake_call()
    asyncio.run(generate_commentary(rep, call))
    content = "\n".join(m["content"] for m in captured["messages"])
    assert "劝退" in content or "price_too_high" in content


def test_prompt_mentions_trajectory_when_present():
    rep = _base_report()
    rep["trajectory"] = [
        {"round_idx": 0, "n_valid": 10, "mean": 4.0, "p25": 3.0, "p75": 5.0},
        {"round_idx": 1, "n_valid": 10, "mean": 6.0, "p25": 5.0, "p75": 7.0},
    ]
    call, captured = _make_fake_call()
    asyncio.run(generate_commentary(rep, call))
    content = "\n".join(m["content"] for m in captured["messages"])
    assert "演化" in content or "trajectory" in content.lower() or "round" in content.lower()


def test_returns_model_text_verbatim():
    call, _ = _make_fake_call("自定义返回内容 123")
    out = asyncio.run(generate_commentary(_base_report(), call))
    assert out == "自定义返回内容 123"
