# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import asyncio
import itertools
import threading

import pytest

from wanxiang.personas.persona import Persona
from wanxiang.simulation.batch import BatchRunner
from wanxiang.simulation.decision import DecisionResult
from wanxiang.simulation.scenario import DecisionKind, ScenarioConfig


def _personas(n):
    return [
        Persona(agent_id=i, name=f"p{i}",
                demographic={"年龄": 20 + i % 10},
                personality={}, media={})
        for i in range(n)
    ]


def _scenario_rate():
    return ScenarioConfig(material="m", question="q",
                          decision_kind=DecisionKind.RATE)


def test_batch_runs_one_decision_per_persona():
    personas = _personas(10)
    counter = itertools.count(start=1)

    async def call(messages):
        return '{"score": ' + str(next(counter)) + '}'

    runner = BatchRunner(decision_concurrency=4)
    results = asyncio.run(runner.run_all(personas, _scenario_rate(), call))
    assert len(results) == 10
    assert all(isinstance(r, DecisionResult) for r in results)
    assert {r.agent_id for r in results} == set(range(10))


def test_batch_results_preserve_persona_order():
    personas = _personas(5)
    counter = itertools.count(start=100)

    async def call(messages):
        return '{"score": ' + str(next(counter)) + '}'

    runner = BatchRunner(decision_concurrency=2)
    results = asyncio.run(runner.run_all(personas, _scenario_rate(), call))
    assert [r.agent_id for r in results] == [0, 1, 2, 3, 4]


def test_batch_concurrency_limit_is_enforced():
    personas = _personas(20)
    in_flight = 0
    peak = 0
    lock = threading.Lock()

    async def call(messages):
        nonlocal in_flight, peak
        with lock:
            in_flight += 1
            peak = max(peak, in_flight)
        await asyncio.sleep(0.02)
        with lock:
            in_flight -= 1
        return '{"score": 5}'

    runner = BatchRunner(decision_concurrency=3)
    asyncio.run(runner.run_all(personas, _scenario_rate(), call))
    assert peak <= 3, f"peak in-flight {peak} exceeded concurrency limit 3"
    assert peak >= 2


def test_batch_does_not_raise_on_individual_failures():
    personas = _personas(6)

    async def call(messages):
        system = messages[0]["content"]
        if "p3" in system:
            raise RuntimeError("boom for p3")
        return '{"score": 7}'

    runner = BatchRunner(decision_concurrency=4)
    results = asyncio.run(runner.run_all(personas, _scenario_rate(), call))
    assert len(results) == 6
    errs = [r for r in results if r.error]
    oks = [r for r in results if r.error is None]
    assert len(errs) == 1 and errs[0].agent_id == 3
    assert len(oks) == 5 and all(r.value == 7 for r in oks)


def test_batch_empty_personas_returns_empty():
    runner = BatchRunner(decision_concurrency=4)
    results = asyncio.run(runner.run_all([], _scenario_rate(),
                                          lambda m: None))  # noqa
    assert results == []
