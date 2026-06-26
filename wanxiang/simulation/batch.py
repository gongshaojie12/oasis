# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""BatchRunner: 并发跑 N 个 agent 的 decision_only 模拟。

用 asyncio.Semaphore 限制同时挂起的 model 调用数。永远返回 N 个
DecisionResult（DecisionRunner 已保证错误装 error 不抛），调用方按
result.error is None 过滤。
"""
from __future__ import annotations

import asyncio
from typing import Callable, Iterable, Optional

from wanxiang.personas.persona import Persona
from wanxiang.simulation.decision import (DecisionResult, DecisionRunner,
                                          ModelCall)
from wanxiang.simulation.scenario import ScenarioConfig

# progress_cb(done, total, partial_results, persona, result) —— 每完成一个
# agent 调一次。persona/result 是刚完成的那个 agent(即 partial_results 末尾
# 那条对应的 persona)。partial_results 顺序无关,仅供运行态聚合(如均值)。
ProgressCb = Callable[
    [int, int, list[DecisionResult], Persona, DecisionResult], None]


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
        *,
        progress_cb: Optional[ProgressCb] = None,
    ) -> list[DecisionResult]:
        personas_list = list(personas)
        if not personas_list:
            return []
        total = len(personas_list)
        sem = asyncio.Semaphore(self.decision_concurrency)
        # 顺序无关地收集已完成结果，供 progress_cb 做运行态聚合。
        done_results: list[DecisionResult] = []

        async def one(p: Persona) -> DecisionResult:
            async with sem:
                res = await self._runner.run(p, scenario, model_call)
            done_results.append(res)
            if progress_cb is not None:
                # 回调内任何异常都不能影响模拟本身。
                try:
                    progress_cb(len(done_results), total, done_results, p, res)
                except Exception:  # noqa: BLE001
                    pass
            return res

        return await asyncio.gather(*(one(p) for p in personas_list))
