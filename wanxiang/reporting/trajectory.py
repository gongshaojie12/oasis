# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""M6+: 群体情绪演化曲线 (sentiment trajectory)。

输入：rounds: list[list[DecisionResult]]，每轮是一份决策结果快照。
输出：list[TrajectoryPoint]，按 round_idx 0..N-1 排序。

只对数值 kind 有意义 (RATE/SENTIMENT/CLICK_PROBABILITY/WTP)。
非数值 kind (CHOOSE) 触发 ValueError。
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Iterable

from wanxiang.simulation.decision import DecisionResult

_NUMERIC_KINDS = {"rate", "sentiment", "click_probability",
                   "willingness_to_pay", "wtp"}


@dataclass(frozen=True)
class TrajectoryPoint:
    round_idx: int      # 0 = round 0 (baseline / pre-social), 1..N = after each round
    n_valid: int
    mean: float | None
    p25: float | None
    p75: float | None


def _stats(values: list[float]) -> tuple[float, float, float] | tuple[None, None, None]:
    if not values:
        return (None, None, None)
    mean = statistics.fmean(values)
    if len(values) == 1:
        return (mean, mean, mean)
    qs = statistics.quantiles(values, n=4, method="exclusive")
    return (mean, qs[0], qs[2])


def build_trajectory(
    rounds: Iterable[Iterable[DecisionResult]],
    kind: str,
) -> list[TrajectoryPoint]:
    """为每一轮计算 (n_valid, mean, p25, p75)。"""
    if kind not in _NUMERIC_KINDS:
        raise ValueError(
            f"build_trajectory requires numeric kind, got {kind!r}")

    rounds_list = [list(r) for r in rounds]
    out: list[TrajectoryPoint] = []
    for i, round_results in enumerate(rounds_list):
        valid_values = [float(r.value) for r in round_results
                         if r.error is None and r.value is not None]
        mean, p25, p75 = _stats(valid_values)
        out.append(TrajectoryPoint(
            round_idx=i,
            n_valid=len(valid_values),
            mean=mean, p25=p25, p75=p75,
        ))
    return out
