# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""make_stub_call 现应返回合规 JSON 而非 Lorem Ipsum。"""
import asyncio
import json

from wanxiang.models import make_stub_call


def test_stub_call_returns_valid_json_for_rate_prompt():
    call = make_stub_call()
    out = asyncio.run(call([
        {"role": "system", "content": "你是测试用户"},
        {"role": "user", "content": "请给出 score 0-10"}
    ]))
    data = json.loads(out)
    assert "score" in data
    assert isinstance(data["score"], int)
    assert 0 <= data["score"] <= 10


def test_stub_call_returns_valid_json_for_choose_prompt():
    call = make_stub_call()
    out = asyncio.run(call([
        {"role": "system", "content": "你是测试用户"},
        {"role": "user", "content":
            "【材料】m\n【可选项】青提 / 白桃 / 海盐荔枝\n【问题】请选 option"}
    ]))
    data = json.loads(out)
    assert "option" in data
    assert data["option"] in {"青提", "白桃", "海盐荔枝"}


def test_stub_call_deterministic_for_same_messages():
    call = make_stub_call()
    msgs = [{"role": "user", "content": "score please"}]
    a = asyncio.run(call(msgs))
    b = asyncio.run(call(msgs))
    assert a == b  # 同样的输入 → 同样的输出


def test_stub_call_varies_by_system_prompt():
    """不同 persona（不同 system prompt）应产生不同输出，让 aggregate 有分布。"""
    call = make_stub_call()
    a = asyncio.run(call([
        {"role": "system", "content": "你是 persona A"},
        {"role": "user", "content": "score please"},
    ]))
    b = asyncio.run(call([
        {"role": "system", "content": "你是 persona B"},
        {"role": "user", "content": "score please"},
    ]))
    # 大概率不同（小概率撞 hash 相等，可以容忍——本测试有 1/10 假阴性概率）
    # 用多组确保：
    diffs = 0
    for i in range(10):
        x = asyncio.run(call([
            {"role": "system", "content": f"persona {i}"},
            {"role": "user", "content": "score please"},
        ]))
        if x != a:
            diffs += 1
    assert diffs >= 5, "stub 应大体上对不同 persona 给不同回答"
