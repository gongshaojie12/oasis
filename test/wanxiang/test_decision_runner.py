# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import asyncio

import pytest

from wanxiang.personas.persona import Persona
from wanxiang.simulation.decision import DecisionResult, DecisionRunner
from wanxiang.simulation.scenario import DecisionKind, ScenarioConfig


def _persona(agent_id=0, name="阿哲"):
    return Persona(agent_id=agent_id, name=name,
                   demographic={"年龄": 25, "城市": "上海"},
                   personality={"价格敏感度": 0.4},
                   media={"小红书": 0.8})


def _scenario_rate():
    return ScenarioConfig(material="新品 ¥6", question="买不买，0-10 评分",
                          decision_kind=DecisionKind.RATE)


def _scenario_choose():
    return ScenarioConfig(material="三口味", question="挑一个",
                          decision_kind=DecisionKind.CHOOSE,
                          options=("青提", "白桃", "海盐荔枝"))


def _make_call(response_text):
    captured = {"messages": None}

    async def call(messages):
        captured["messages"] = messages
        return response_text

    return call, captured


def test_runner_returns_decision_result_for_rate():
    call, captured = _make_call('{"score": 7}')
    runner = DecisionRunner()
    res = asyncio.run(runner.run(_persona(), _scenario_rate(), call))
    assert isinstance(res, DecisionResult)
    assert res.agent_id == 0
    assert res.kind is DecisionKind.RATE
    assert res.value == 7
    assert res.error is None


def test_runner_returns_decision_result_for_choose():
    call, _ = _make_call('{"option": "白桃"}')
    runner = DecisionRunner()
    res = asyncio.run(runner.run(_persona(), _scenario_choose(), call))
    assert res.kind is DecisionKind.CHOOSE
    assert res.value == "白桃"
    assert res.error is None


def test_runner_passes_system_and_user_messages_to_model():
    call, captured = _make_call('{"score": 5}')
    runner = DecisionRunner()
    asyncio.run(runner.run(_persona(name="小张"), _scenario_rate(), call))
    msgs = captured["messages"]
    assert isinstance(msgs, list) and len(msgs) == 2
    assert msgs[0]["role"] == "system"
    assert "小张" in msgs[0]["content"]
    assert msgs[1]["role"] == "user"
    assert "新品" in msgs[1]["content"]


def test_malformed_json_returns_error_result_not_raise():
    call, _ = _make_call("我觉得 6 分")
    runner = DecisionRunner()
    res = asyncio.run(runner.run(_persona(), _scenario_rate(), call))
    assert res.value is None
    assert res.error and "json" in res.error.lower()


def test_missing_required_field_returns_error_result():
    call, _ = _make_call('{"foo": 1}')
    runner = DecisionRunner()
    res = asyncio.run(runner.run(_persona(), _scenario_rate(), call))
    assert res.value is None
    assert res.error and "score" in res.error


def test_choose_value_not_in_options_returns_error_result():
    call, _ = _make_call('{"option": "百香果"}')
    runner = DecisionRunner()
    res = asyncio.run(runner.run(_persona(), _scenario_choose(), call))
    assert res.value is None
    assert res.error and "options" in res.error


def test_runner_strips_code_fence_around_json():
    call, _ = _make_call('```json\n{"score": 9}\n```')
    runner = DecisionRunner()
    res = asyncio.run(runner.run(_persona(), _scenario_rate(), call))
    assert res.value == 9
    assert res.error is None


def test_runner_captures_model_exception():
    async def call(messages):
        raise RuntimeError("network down")
    runner = DecisionRunner()
    res = asyncio.run(runner.run(_persona(), _scenario_rate(), call))
    assert res.value is None
    assert res.error and "network down" in res.error
