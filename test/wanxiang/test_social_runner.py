# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import asyncio
import itertools

import pytest

from wanxiang.personas.persona import Persona
from wanxiang.simulation.scenario import DecisionKind, ScenarioConfig
from wanxiang.simulation.social import SocialRoundsRunner, format_peer_signal
from wanxiang.simulation.aggregate import AggregateReport
from wanxiang.simulation.decision import DecisionResult


def _personas(n):
    return [Persona(agent_id=i, name=f"p{i}",
                    demographic={"年龄": 20}, personality={}, media={})
            for i in range(n)]


def _scenario_rate():
    return ScenarioConfig(material="m", question="0-10 评分",
                          decision_kind=DecisionKind.RATE)


def _scenario_choose():
    return ScenarioConfig(material="m", question="选一个",
                          decision_kind=DecisionKind.CHOOSE,
                          options=("A", "B", "C"))


# ---- format_peer_signal ----

def test_format_peer_signal_choose_includes_top_and_share():
    rep = AggregateReport(
        kind=DecisionKind.CHOOSE, n_total=100, n_valid=100,
        error_count=0, error_rate=0.0,
        stats={"counts": {"A": 60, "B": 30, "C": 10},
               "share": {"A": 0.6, "B": 0.3, "C": 0.1}, "top": "A"})
    sig = format_peer_signal(rep)
    assert "A" in sig and "60" in sig  # 包含首选与份额


def test_format_peer_signal_rate_includes_mean():
    rep = AggregateReport(
        kind=DecisionKind.RATE, n_total=100, n_valid=100,
        error_count=0, error_rate=0.0,
        stats={"mean": 7.2, "median": 7, "p25": 5, "p75": 9,
               "min": 1, "max": 10})
    sig = format_peer_signal(rep)
    assert "7.2" in sig or "7.20" in sig


def test_format_peer_signal_empty_returns_neutral_text():
    rep = AggregateReport(kind=None, n_total=0, n_valid=0,
                          error_count=0, error_rate=0.0, stats={})
    sig = format_peer_signal(rep)
    # 不抛；返回非空中立文案
    assert isinstance(sig, str) and len(sig) > 0


# ---- SocialRoundsRunner ----

def test_runner_returns_n_results_and_history():
    personas = _personas(8)
    counter = itertools.count(1)

    async def call(messages):
        # 每次返回 score=1,2,3...
        return '{"score": ' + str(next(counter)) + '}'

    runner = SocialRoundsRunner(rounds=2, decision_concurrency=4)
    final, history = asyncio.run(
        runner.run(personas, _scenario_rate(), call))
    assert len(final) == 8
    assert all(isinstance(r, DecisionResult) for r in final)
    # history: 初始 round + R 轮 = R+1 共 rounds=2 时 → 3 个快照
    assert len(history) == 3
    assert all(len(round_results) == 8 for round_results in history)


def test_runner_rounds_zero_equals_decision_only():
    """rounds=0 等价于只跑 round 0；final 与 history[0] 相同。"""
    personas = _personas(5)

    async def call(messages):
        return '{"score": 5}'

    runner = SocialRoundsRunner(rounds=0, decision_concurrency=4)
    final, history = asyncio.run(
        runner.run(personas, _scenario_rate(), call))
    assert len(history) == 1
    assert [r.value for r in final] == [r.value for r in history[0]]


def test_peer_signal_injected_into_later_rounds_user_message():
    """从 round 1 开始，user message 应包含 peer signal 文本。"""
    captured_messages = []

    async def call(messages):
        captured_messages.append(messages[-1]["content"])  # user 消息
        return '{"score": 5}'

    personas = _personas(3)
    runner = SocialRoundsRunner(rounds=1, decision_concurrency=2)
    asyncio.run(runner.run(personas, _scenario_rate(), call))
    # 共 3 personas * 2 rounds = 6 次 model 调用
    assert len(captured_messages) == 6
    # round 0 的 user message 不应含 peer signal 标记；round 1 的应含
    round0_msgs = captured_messages[:3]
    round1_msgs = captured_messages[3:]
    assert all("【同辈参考】" not in m for m in round0_msgs)
    assert all("【同辈参考】" in m for m in round1_msgs)


def test_runner_rounds_validation():
    with pytest.raises(ValueError):
        SocialRoundsRunner(rounds=-1, decision_concurrency=4)


def test_runner_choose_kind_works():
    personas = _personas(4)
    seq = itertools.cycle(["A", "A", "B", "C"])

    async def call(messages):
        return '{"option": "' + next(seq) + '"}'

    runner = SocialRoundsRunner(rounds=2, decision_concurrency=4)
    final, history = asyncio.run(
        runner.run(personas, _scenario_choose(), call))
    assert len(final) == 4
    # 选项落在 options 内
    assert all(r.value in {"A", "B", "C"} for r in final if r.error is None)
