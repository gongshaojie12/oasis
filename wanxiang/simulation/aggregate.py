# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""把 list[DecisionResult] 聚合成群体分布报告。

数值 kind (RATE/CLICK_PROBABILITY/SENTIMENT/WTP) → mean/median/p25/p75
枚举 kind (CHOOSE) → counts/share/top
始终报告 error_count / error_rate；错误样本不参与数值统计。
"""
from __future__ import annotations

import statistics
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Iterable

from wanxiang.simulation.decision import DecisionResult
from wanxiang.simulation.scenario import DecisionKind

_NUMERIC_KINDS = {
    DecisionKind.RATE,
    DecisionKind.CLICK_PROBABILITY,
    DecisionKind.SENTIMENT,
    DecisionKind.WTP,
}


@dataclass(frozen=True)
class AggregateReport:
    kind: DecisionKind | None
    n_total: int
    n_valid: int
    error_count: int
    error_rate: float
    stats: dict[str, Any] = field(default_factory=dict)


def _quantiles(values: list[float]) -> tuple[float, float, float]:
    """返回 (p25, median, p75)。values 必须非空。"""
    if len(values) == 1:
        v = float(values[0])
        return v, v, v
    qs = statistics.quantiles(values, n=4, method="exclusive")
    return qs[0], qs[1], qs[2]


def _histogram(values: list[float], kind: DecisionKind) -> list[dict]:
    """直方图(供前端画分布柱状图)。返回 [{label, count}] 有序桶。

    - RATE: 固定 0..10 共 11 个整数桶(评分本就是整数)。
    - 其他数值 kind: 在 [min,max] 上等宽分 10 桶;退化(全相等)→ 单桶。
    """
    if not values:
        return []
    if kind is DecisionKind.RATE:
        counts = {i: 0 for i in range(11)}
        for v in values:
            b = max(0, min(10, int(round(v))))
            counts[b] += 1
        return [{"label": str(i), "count": counts[i]} for i in range(11)]

    lo, hi = min(values), max(values)
    if hi <= lo:
        return [{"label": f"{lo:.2f}", "count": len(values)}]
    bins = 10
    width = (hi - lo) / bins
    counts = [0] * bins
    for v in values:
        idx = int((v - lo) / width)
        if idx >= bins:
            idx = bins - 1
        counts[idx] += 1
    out = []
    for i in range(bins):
        left = lo + i * width
        out.append({"label": f"{left:.2f}", "count": counts[i]})
    return out


def aggregate(results: Iterable[DecisionResult]) -> AggregateReport:
    items = list(results)
    n_total = len(items)
    if n_total == 0:
        return AggregateReport(kind=None, n_total=0, n_valid=0,
                                error_count=0, error_rate=0.0, stats={})

    kinds = {r.kind for r in items}
    if len(kinds) > 1:
        raise ValueError(f"cannot aggregate mixed decision kinds: {kinds}")
    kind = next(iter(kinds))

    valid = [r for r in items if r.error is None]
    n_valid = len(valid)
    n_err = n_total - n_valid
    error_rate = n_err / n_total

    if n_valid == 0:
        return AggregateReport(kind=kind, n_total=n_total, n_valid=0,
                                error_count=n_err, error_rate=error_rate,
                                stats={})

    stats: dict[str, Any] = {}
    if kind in _NUMERIC_KINDS:
        nums = [float(r.value) for r in valid]
        p25, median, p75 = _quantiles(nums)
        stats = {
            "mean": statistics.fmean(nums),
            "median": median,
            "p25": p25,
            "p75": p75,
            "min": min(nums),
            "max": max(nums),
            "histogram": _histogram(nums, kind),
        }
    elif kind is DecisionKind.CHOOSE:
        counter = Counter(r.value for r in valid)
        total = sum(counter.values())
        share = {k: v / total for k, v in counter.items()}
        top_count = max(counter.values())
        top = sorted([k for k, v in counter.items() if v == top_count])[0]
        stats = {"counts": dict(counter), "share": share, "top": top}
    else:
        raise ValueError(f"no aggregator implemented for kind {kind}")

    return AggregateReport(kind=kind, n_total=n_total, n_valid=n_valid,
                            error_count=n_err, error_rate=error_rate,
                            stats=stats)
