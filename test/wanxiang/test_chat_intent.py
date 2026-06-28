# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""parse_intent: NL → SimulateRequest（stub model）。"""
import asyncio
import json

import pytest

from wanxiang.chat.intent import IntentParseResult, parse_intent


# A canned LLM that returns the JSON it's "told to" via the closure
def _scripted(response_text):
    async def call(messages):
        return response_text
    return call


def test_complete_extraction_returns_simulate_request():
    raw = json.dumps({
        "intent": "simulate",
        "fields": {
            "material": "新品「轻气泡」¥6/瓶",
            "question": "你的购买意愿（0-10 评分）",
            "kind": "rate",
            "options": None,
            "n": 100,
            "rounds": 0
        },
        "missing": [],
        "explanation": "已识别为购买意愿打分场景。",
        "confidence": 0.93
    })
    r = asyncio.run(parse_intent(
        "帮我测一线 Z 世代对新品轻气泡 ¥6 的购买意愿",
        model_call=_scripted(raw),
        default_distribution_path="test/wanxiang/fixtures/cn_z_generation_v1.yaml"))
    assert isinstance(r, IntentParseResult)
    assert r.intent == "simulate"
    assert r.missing == []
    assert r.request is not None
    assert r.request.scenario.kind == "rate"
    assert r.request.n == 100
    assert r.request.distribution_path.endswith("cn_z_generation_v1.yaml")
    assert r.confidence > 0.9


def test_choose_kind_with_options():
    raw = json.dumps({
        "intent": "simulate",
        "fields": {
            "material": "三口味候选",
            "question": "最想买哪个？",
            "kind": "choose",
            "options": ["青提", "白桃", "海盐荔枝"],
            "n": 50,
            "rounds": 0
        },
        "missing": [],
        "explanation": "已识别为多选一",
        "confidence": 0.88
    })
    r = asyncio.run(parse_intent(
        "测下青提白桃海盐荔枝三种新品哪个最受欢迎",
        _scripted(raw),
        default_distribution_path="x.yaml"))
    assert r.request.scenario.kind == "choose"
    assert r.request.scenario.options == ["青提", "白桃", "海盐荔枝"]


def test_missing_fields_returned_when_llm_says_so():
    raw = json.dumps({
        "intent": "simulate",
        "fields": {
            "material": "",
            "question": "买不买？",
            "kind": "rate",
            "options": None,
            "n": None,
            "rounds": 0
        },
        "missing": ["material", "n"],
        "explanation": "请补充投放材料与样本数",
        "confidence": 0.5
    })
    r = asyncio.run(parse_intent(
        "随便测一下", _scripted(raw),
        default_distribution_path="x.yaml"))
    assert r.intent == "simulate"
    assert "material" in r.missing
    assert r.request is None  # 不应组装出无效 request


def test_unknown_intent_when_off_topic():
    raw = json.dumps({
        "intent": "unknown",
        "fields": {"material": "", "question": "", "kind": "rate",
                   "options": None, "n": None, "rounds": 0},
        "missing": [],
        "explanation": "这看起来不是模拟需求；想测什么？",
        "confidence": 0.2
    })
    r = asyncio.run(parse_intent(
        "今天天气怎么样", _scripted(raw),
        default_distribution_path="x.yaml"))
    assert r.intent == "unknown"
    assert r.request is None


def test_malformed_llm_output_returns_unknown_with_explanation():
    r = asyncio.run(parse_intent(
        "测点东西", _scripted("不是 JSON"),
        default_distribution_path="x.yaml"))
    assert r.intent == "unknown"
    assert r.request is None
    assert "解析" in r.explanation or "parse" in r.explanation.lower() or \
           "json" in r.explanation.lower()


def test_code_fence_stripped():
    """模型常加 ```json ... ``` 围栏，应能解析。"""
    raw = "```json\n" + json.dumps({
        "intent": "simulate",
        "fields": {"material": "m", "question": "q", "kind": "rate",
                   "options": None, "n": 50, "rounds": 0},
        "missing": [], "explanation": "ok", "confidence": 0.9
    }) + "\n```"
    r = asyncio.run(parse_intent("x", _scripted(raw),
                                  default_distribution_path="x.yaml"))
    assert r.intent == "simulate"
    assert r.request is not None


def test_choose_with_missing_options_auto_added_to_missing():
    """LLM 说是 choose 但没给 options → request 不组装，options 入 missing。"""
    raw = json.dumps({
        "intent": "simulate",
        "fields": {"material": "m", "question": "q", "kind": "choose",
                   "options": None, "n": 50, "rounds": 0},
        "missing": [], "explanation": "需补选项", "confidence": 0.7
    })
    r = asyncio.run(parse_intent("x", _scripted(raw),
                                  default_distribution_path="x.yaml"))
    assert r.request is None
    assert "options" in r.missing


def test_invalid_n_falls_back_to_default_not_missing():
    """人数现在是可选项：非法/缺失的 n 不再算 missing，而是用占位默认值并
    标记 n_explicit=False（路由层会保留任务现有 population_size）。"""
    raw = json.dumps({
        "intent": "simulate",
        "fields": {"material": "m", "question": "q", "kind": "rate",
                   "options": None, "n": -5, "rounds": 0},
        "missing": [], "explanation": "n 无效", "confidence": 0.6
    })
    r = asyncio.run(parse_intent("x", _scripted(raw),
                                  default_distribution_path="x.yaml"))
    assert r.request is not None
    assert "n" not in r.missing
    assert r.n_explicit is False


def test_explicit_n_sets_n_explicit_flag():
    """用户明说人数 → n_explicit=True，request.n 取该值。"""
    raw = json.dumps({
        "intent": "simulate",
        "fields": {"material": "m", "question": "q", "kind": "rate",
                   "options": None, "n": 300, "rounds": 0},
        "missing": [], "explanation": "ok", "confidence": 0.9
    })
    r = asyncio.run(parse_intent("测 300 人", _scripted(raw),
                                  default_distribution_path="x.yaml"))
    assert r.request is not None
    assert r.request.n == 300
    assert r.n_explicit is True


def test_model_call_exception_returns_unknown():
    async def boom(messages):
        raise RuntimeError("net down")
    r = asyncio.run(parse_intent("x", boom,
                                  default_distribution_path="x.yaml"))
    assert r.intent == "unknown"
    assert "net down" in r.explanation
