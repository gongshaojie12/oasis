# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""BatchRunner: 并发跑 N 个 agent 的 decision_only 模拟。

用 asyncio.Semaphore 限制同时挂起的 model 调用数。永远返回 N 个
DecisionResult（DecisionRunner 已保证错误装 error 不抛），调用方按
result.error is None 过滤。
"""
from __future__ import annotations

import asyncio
from typing import Iterable

from wanxiang.personas.persona import Persona
from wanxiang.simulation.decision import (DecisionResult, DecisionRunner,
                                          ModelCall)
from wanxiang.simulation.scenario import ScenarioConfig


class BatchRunner:

    def __init__(self, decision_concurrency: int = 16):
        if decision_concurrency < 1:
            raise ValueError("decision_concurrency must be >= 1")
        self.decision_concurrency = decision_concurrency
        self._runner = DecisionRunner()

    async def run_all(
        self,
        personas: Iterable[Persona],
        scenario: ScenarioConfig,
        model_call: ModelCall,
    ) -> list[DecisionResult]:
        personas_list = list(personas)
        if not personas_list:
            return []
        sem = asyncio.Semaphore(self.decision_concurrency)

        async def one(p: Persona) -> DecisionResult:
            async with sem:
                return await self._runner.run(p, scenario, model_call)

        return await asyncio.gather(*(one(p) for p in personas_list))
