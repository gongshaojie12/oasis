# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""decision_only 模式端到端冒烟：分布→造人→并发模拟→聚合。

不接真实 LLM；用一个会"参考画像"决定输出的 stub 来证明主链
能跑通且 BatchRunner+aggregate 给出合理分布。
"""
import asyncio

import pytest

from wanxiang.personas import PersonaBuilder
from wanxiang.simulation import (BatchRunner, DecisionKind, ScenarioConfig,
                                 aggregate)


SIMPLE_DIST = {
    "demographic": {
        "城市": [("北京", 0.5), ("上海", 0.5)],
    },
    "personality": {
        "价格敏感度": [(0.2, 0.5), (0.8, 0.5)],
    },
    "media": {},
}


def test_decision_only_main_chain_end_to_end():
    pb = PersonaBuilder()
    personas = pb.sample(SIMPLE_DIST, n=1000, seed=2026)

    scenario = ScenarioConfig(
        material="新品定价 ¥10", question="给出 0-10 购买意愿评分",
        decision_kind=DecisionKind.RATE)

    async def stub_call(messages):
        sys = messages[0]["content"]
        if "价格敏感度：0.8" in sys:
            return '{"score": 2}'
        return '{"score": 8}'

    runner = BatchRunner(decision_concurrency=32)
    results = asyncio.run(runner.run_all(personas, scenario, stub_call))

    report = aggregate(results)
    assert report.n_total == 1000
    assert report.error_count == 0
    assert 4.7 <= report.stats["mean"] <= 5.3
    assert report.stats["min"] == 2
    assert report.stats["max"] == 8
