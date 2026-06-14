# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""DecisionRunner / BatchRunner inject media feed into system prompt
when scenario carries media_pool + feed_k > 0."""
from __future__ import annotations

import asyncio

import pytest

from wanxiang.media.environment import MediaItem
from wanxiang.personas.persona import Persona
from wanxiang.simulation.batch import BatchRunner
from wanxiang.simulation.decision import DecisionRunner
from wanxiang.simulation.scenario import DecisionKind, ScenarioConfig


def _persona(agent_id=0, name="阿哲",
              media=None, personality=None):
    return Persona(
        agent_id=agent_id, name=name,
        demographic={"年龄": 25, "城市": "上海"},
        personality=personality or {"interests": ["coffee"]},
        media=media if media is not None else {"xhs": 0.8})


def _make_call():
    captured = {"messages": None}

    async def call(messages):
        captured["messages"] = messages
        return '{"score": 7}'

    return call, captured


def test_no_media_pool_no_feed_in_prompt():
    """Baseline backwards-compat: empty media_pool → no feed marker."""
    call, captured = _make_call()
    sc = ScenarioConfig(material="x", question="?",
                        decision_kind=DecisionKind.RATE)
    asyncio.run(DecisionRunner().run(_persona(), sc, call))
    sys_msg = next(m for m in captured["messages"] if m["role"] == "system")
    assert "信息流" not in sys_msg["content"]


def test_with_media_pool_feed_appears_in_system_prompt():
    call, captured = _make_call()
    pool = (MediaItem(item_id="a", title="精品咖啡推荐",
                       body="今天试了X牌咖啡",
                       channel="xhs", tags=("coffee",)),)
    sc = ScenarioConfig(material="x", question="?",
                        decision_kind=DecisionKind.RATE,
                        media_pool=pool, feed_k=1)
    asyncio.run(DecisionRunner().run(_persona(), sc, call))
    sys_msg = next(m for m in captured["messages"] if m["role"] == "system")
    assert "信息流" in sys_msg["content"]
    assert "精品咖啡推荐" in sys_msg["content"]
    assert "xhs" in sys_msg["content"]


def test_feed_k_zero_no_injection_even_with_pool():
    call, captured = _make_call()
    pool = (MediaItem(item_id="a", title="t", body="b", channel="xhs"),)
    sc = ScenarioConfig(material="x", question="?",
                        decision_kind=DecisionKind.RATE,
                        media_pool=pool, feed_k=0)
    asyncio.run(DecisionRunner().run(_persona(), sc, call))
    sys_msg = next(m for m in captured["messages"] if m["role"] == "system")
    assert "信息流" not in sys_msg["content"]


def test_feed_appears_before_persona_context():
    """Feed prefix should sit at top of system prompt, before persona section."""
    call, captured = _make_call()
    pool = (MediaItem(item_id="a", title="独家爆款", body="b", channel="xhs"),)
    sc = ScenarioConfig(material="x", question="?",
                        decision_kind=DecisionKind.RATE,
                        media_pool=pool, feed_k=1)
    asyncio.run(DecisionRunner().run(_persona(name="小张"), sc, call))
    sys = next(m for m in captured["messages"] if m["role"] == "system")["content"]
    # feed should be before persona name
    assert sys.index("独家爆款") < sys.index("小张")


def test_feed_caps_at_k_even_if_pool_larger():
    """K=2 with 5 items → exactly 2 entries injected (numbered 1./2., no 3.)."""
    call, captured = _make_call()
    pool = tuple(MediaItem(item_id=f"i{i}", title=f"标题{i}", body="",
                            channel="xhs", tags=("coffee",))
                 for i in range(5))
    sc = ScenarioConfig(material="x", question="?",
                        decision_kind=DecisionKind.RATE,
                        media_pool=pool, feed_k=2)
    asyncio.run(DecisionRunner().run(_persona(), sc, call))
    sys = next(m for m in captured["messages"] if m["role"] == "system")["content"]
    # bracket the numbered markers so we don't match "10." or substrings
    assert "1." in sys
    assert "2." in sys
    assert "3." not in sys


def test_batch_runner_also_injects_per_persona():
    """BatchRunner should inject feed for every persona it dispatches."""
    seen = []

    async def call(messages):
        sys = next(m for m in messages if m["role"] == "system")["content"]
        seen.append(sys)
        return '{"score": 5}'

    pool = (
        MediaItem(item_id="x", title="xhs内容", body="b", channel="xhs"),
        MediaItem(item_id="d", title="douyin内容", body="b", channel="douyin"),
    )
    sc = ScenarioConfig(material="x", question="?",
                        decision_kind=DecisionKind.RATE,
                        media_pool=pool, feed_k=1)
    p1 = _persona(agent_id=1, name="A", media={"xhs": 0.9})
    p2 = _persona(agent_id=2, name="B", media={"douyin": 0.9})

    runner = BatchRunner(decision_concurrency=2)
    asyncio.run(runner.run_all([p1, p2], sc, call))

    joined = "\n".join(seen)
    # both top items should have been picked up — for some persona
    assert "xhs内容" in joined
    assert "douyin内容" in joined
