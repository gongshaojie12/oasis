# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""simulation: 场景配置 / 决策运行器 / 批量并发 / 聚合（spec §M3/M4 decision_only）。"""
from wanxiang.simulation.scenario import DecisionKind, ScenarioConfig
from wanxiang.simulation.decision import (DecisionResult, DecisionRunner,
                                          ModelCall)
from wanxiang.simulation.batch import BatchRunner
from wanxiang.simulation.aggregate import AggregateReport, aggregate

__all__ = [
    "DecisionKind", "ScenarioConfig",
    "DecisionResult", "DecisionRunner", "ModelCall",
    "BatchRunner", "AggregateReport", "aggregate",
]
