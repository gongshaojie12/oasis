# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""P4: parse_intent supports locale=zh|en (system prompt language)."""
from __future__ import annotations

import asyncio
import json

from wanxiang.chat.intent import IntentParseResult, parse_intent


def _capture():
    captured = {"messages": None}

    async def call(messages):
        captured["messages"] = messages
        return json.dumps({
            "intent": "simulate",
            "fields": {
                "material": "Ad copy", "question": "Would you buy?",
                "kind": "rate", "options": None, "n": 50, "rounds": 0,
            },
            "missing": [],
            "explanation": "ok",
            "confidence": 0.9,
        })

    return call, captured


def test_default_locale_uses_chinese_system_prompt():
    call, captured = _capture()
    asyncio.run(parse_intent("帮我测一下购买意愿", call,
                              default_distribution_path="x.yaml"))
    sys_content = captured["messages"][0]["content"]
    assert "万象" in sys_content or "WANXIANG" in sys_content
    # core zh keywords
    assert "决策" in sys_content or "评分" in sys_content


def test_en_locale_uses_english_system_prompt():
    call, captured = _capture()
    asyncio.run(parse_intent("Test buy intent for new product", call,
                              default_distribution_path="x.yaml", locale="en"))
    sys_content = captured["messages"][0]["content"]
    # English prompt
    assert "WANXIANG" in sys_content
    # Should not contain core zh instruction prose
    import re
    # allow brand if also present, but check english instructional phrases
    assert "JSON" in sys_content
    assert "intent" in sys_content
    # Should not have substantial Chinese characters (a few brand chars OK)
    cjk = re.findall(r"[一-鿿]", sys_content)
    assert len(cjk) <= 4  # brand "万象" ok, no full sentences in zh


def test_en_locale_still_parses_user_text_correctly():
    """Output structure must be identical regardless of locale."""
    call, _ = _capture()
    r = asyncio.run(parse_intent("Test buy intent", call,
                                  default_distribution_path="x.yaml",
                                  locale="en"))
    assert isinstance(r, IntentParseResult)
    assert r.intent == "simulate"
    assert r.request is not None
    assert r.request.scenario.kind == "rate"
    assert r.request.n == 50


def test_output_intent_result_structure_identical_zh_vs_en():
    call_zh, _ = _capture()
    call_en, _ = _capture()
    r_zh = asyncio.run(parse_intent("x", call_zh,
                                     default_distribution_path="x.yaml"))
    r_en = asyncio.run(parse_intent("x", call_en,
                                     default_distribution_path="x.yaml",
                                     locale="en"))
    assert r_zh.intent == r_en.intent
    assert r_zh.request.scenario.kind == r_en.request.scenario.kind
    assert r_zh.request.n == r_en.request.n
    assert r_zh.confidence == r_en.confidence
