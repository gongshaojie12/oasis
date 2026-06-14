# ============= Copyright 2026 @ WANXIANG. All Rights Reserved. =============
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
# ===========================================================================
"""engine.agent_runtime — agent 执行运行时 (spec §3.1).

OASIS 原 ``SocialAgent`` 的"运行单个 agent 决策"机制在 wanxiang 中分解为：
- ``wanxiang.simulation.decision.DecisionRunner`` —— 单 agent 单次决策
- ``wanxiang.simulation.batch.BatchRunner`` —— 并发批量决策
- ``wanxiang.simulation.social.SocialRoundsRunner`` —— 多轮社交 + 回流决策

本模块按 spec §3.1 的位置约定 re-export 这三个 runner，作为引擎层"agent
运行时"的统一入口。后续若需要做 step-level orchestration，扩展点在此。
"""
from wanxiang.simulation.decision import (DecisionRunner, DecisionResult,
                                            DecisionKind)
from wanxiang.simulation.batch import BatchRunner
from wanxiang.simulation.social import SocialRoundsRunner

__all__ = [
    "DecisionRunner", "DecisionResult", "DecisionKind",
    "BatchRunner", "SocialRoundsRunner",
]
