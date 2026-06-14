# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""P4: generate_commentary supports locale=zh|en (prompt language)."""
from __future__ import annotations

import asyncio

from wanxiang.reporting.commentary import generate_commentary


def _capture(reply="ok"):
    captured = {"messages": None}

    async def call(messages):
        captured["messages"] = messages
        return reply

    return call, captured


def _base_report():
    return {
        "scenario": {"decision_kind": "rate",
                      "question": "0-10 purchase intent",
                      "material": "New product"},
        "persona_count": 100,
        "n_total": 100, "n_valid": 95, "error_count": 5, "error_rate": 0.05,
        "recommendation": {"mean": 6.8,
                           "confidence_band": (5.0, 8.0),
                           "range": (1, 10)},
        "breakdown": [],
        "fidelity": None, "causal": None, "counterfactual": None,
    }


def test_default_zh_prompt_contains_chinese_word_constraint():
    call, captured = _capture()
    asyncio.run(generate_commentary(_base_report(), call))
    content = "\n".join(m["content"] for m in captured["messages"])
    # zh prompt: 中文 + 字数限制
    assert "中文" in content or "字" in content


def test_en_prompt_contains_english_word_constraint():
    call, captured = _capture()
    asyncio.run(generate_commentary(_base_report(), call, locale="en"))
    content = "\n".join(m["content"] for m in captured["messages"])
    # en prompt should mention English / words
    assert "words" in content.lower() or "English" in content
    # And not contain heavy zh prompt instructions
    assert "中文" not in content
    assert "执行摘要" not in content


def test_en_prompt_does_not_leak_zh_section_headings():
    call, captured = _capture()
    asyncio.run(generate_commentary(_base_report(), call, locale="en"))
    content = "\n".join(m["content"] for m in captured["messages"])
    # zh section headings should not appear
    assert "【场景】" not in content
    assert "【核心结果】" not in content
    assert "【输出要求】" not in content
    # English section markers expected
    assert "[Scenario]" in content or "Scenario" in content
