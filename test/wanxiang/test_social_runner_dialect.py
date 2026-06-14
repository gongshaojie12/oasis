# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""SocialRoundsRunner with PlatformDialect injection."""
import asyncio
import os

import pytest

from wanxiang.actions.dialect import DialectLoader
from wanxiang.personas.persona import Persona
from wanxiang.simulation.scenario import DecisionKind, ScenarioConfig
from wanxiang.simulation.social import SocialRoundsRunner

DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "..", "wanxiang", "actions", "l3_dialects")


def _personas(n):
    return [Persona(agent_id=i, name=f"p{i}",
                    demographic={}, personality={}, media={})
            for i in range(n)]


def test_runner_without_dialect_works_as_before():
    personas = _personas(4)
    captured = []

    async def call(messages):
        captured.append(messages[-1]["content"])
        return '{"score": 5}'

    runner = SocialRoundsRunner(rounds=1)
    _final, _hist = asyncio.run(runner.run(
        personas,
        ScenarioConfig(material="m", question="0-10 评分",
                       decision_kind=DecisionKind.RATE),
        call))
    # round 1 的 user msg 含旧的 【同辈参考】 文案
    round1 = captured[len(personas):]
    assert all("【同辈参考】" in m for m in round1)


def test_runner_with_wechat_dialect_injects_friends_signal():
    d = DialectLoader(DIR).load("wechat")
    personas = _personas(4)
    captured = []

    async def call(messages):
        captured.append(messages[-1]["content"])
        return '{"score": 5}'

    runner = SocialRoundsRunner(rounds=1, dialect=d)
    asyncio.run(runner.run(
        personas,
        ScenarioConfig(material="m", question="0-10 评分",
                       decision_kind=DecisionKind.RATE),
        call))
    round1 = captured[len(personas):]
    assert all("好友" in m for m in round1)


def test_runner_with_douyin_dialect_uses_recommend_signal():
    d = DialectLoader(DIR).load("douyin")
    personas = _personas(4)
    captured = []

    async def call(messages):
        captured.append(messages[-1]["content"])
        return '{"score": 5}'

    runner = SocialRoundsRunner(rounds=1, dialect=d)
    asyncio.run(runner.run(
        personas,
        ScenarioConfig(material="m", question="0-10 评分",
                       decision_kind=DecisionKind.RATE),
        call))
    round1 = captured[len(personas):]
    assert all(("推荐" in m or "算法" in m) for m in round1)
