# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""把模拟分布对齐 ground-truth 分布，输出 Spearman/RMSE/欧氏距离与
保真度显示标签（0-1）。

spec §M5（轻量版护城河）。MVP 不依赖 scipy；所有统计用 stdlib 自实现。
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field

from wanxiang.simulation.aggregate import AggregateReport
from wanxiang.simulation.scenario import DecisionKind


@dataclass(frozen=True)
class FidelityReport:
    spearman: float
    rmse: float
    euclidean: float
    fidelity_score: float  # 0..1 显示用，heuristic
    notes: list[str] = field(default_factory=list)


# ---------- 内部统计工具 ----------

def _rank(values: list[float]) -> list[float]:
    """平均秩处理 ties。例如 [10,20,20,30] -> [1, 2.5, 2.5, 4]。"""
    n = len(values)
    indexed = sorted(range(n), key=lambda i: values[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and values[indexed[j + 1]] == values[indexed[i]]:
            j += 1
        avg = (i + j) / 2 + 1  # 1-based 平均秩
        for k in range(i, j + 1):
            ranks[indexed[k]] = avg
        i = j + 1
    return ranks


def _pearson(xs: list[float], ys: list[float]) -> float:
    """Pearson 相关系数；零方差时返回 1.0（约定：序列完全一致 -> 完美）。"""
    n = len(xs)
    if n == 0:
        return 0.0
    mx = statistics.fmean(xs)
    my = statistics.fmean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    denx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    deny = math.sqrt(sum((y - my) ** 2 for y in ys))
    if denx == 0 and deny == 0:
        return 1.0  # 两侧都常数 -> 视为完全一致
    if denx == 0 or deny == 0:
        return 0.0
    return num / (denx * deny)


def _spearman(xs: list[float], ys: list[float]) -> float:
    return _pearson(_rank(xs), _rank(ys))


def _rmse(xs: list[float], ys: list[float]) -> float:
    if not xs:
        return 0.0
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(xs, ys)) / len(xs))


def _euclidean(xs: list[float], ys: list[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(xs, ys)))


def _fidelity_from_rmse(rmse: float) -> float:
    """0-1 显示标签：clip(1 - rmse, 0, 1)。

    适合 0-1 区间的份额向量；超过 1 的 RMSE 直接显示 0。
    """
    return max(0.0, min(1.0, 1.0 - rmse))


# ---------- 公开 API ----------

def calibrate_categorical(
    sim_share: dict[str, float],
    truth_share: dict[str, float],
) -> FidelityReport:
    """对齐两份份额向量并计算保真度指标。"""
    notes: list[str] = []
    only_in_truth = sorted(set(truth_share.keys()) - set(sim_share.keys()))
    only_in_sim = sorted(set(sim_share.keys()) - set(truth_share.keys()))
    if only_in_truth:
        notes.append(f"missing in sim: {only_in_truth}")
    if only_in_sim:
        notes.append(f"missing in truth: {only_in_sim}")

    keys = sorted(set(sim_share.keys()) | set(truth_share.keys()))
    sim_v = [float(sim_share.get(k, 0.0)) for k in keys]
    tru_v = [float(truth_share.get(k, 0.0)) for k in keys]

    spear = _spearman(sim_v, tru_v)
    rmse = _rmse(sim_v, tru_v)
    eucl = _euclidean(sim_v, tru_v)
    fid = _fidelity_from_rmse(rmse)
    return FidelityReport(spearman=spear, rmse=rmse, euclidean=eucl,
                          fidelity_score=fid, notes=notes)


def calibrate_numeric(
    sim_stats: dict,
    truth_stats: dict,
) -> FidelityReport:
    """数值 kind 的轻量版：先只比 mean。

    后续可扩展 p25/p75 等向量比较；MVP 用 mean 一点。
    """
    if "mean" not in sim_stats:
        raise KeyError("sim_stats requires 'mean'")
    if "mean" not in truth_stats:
        raise KeyError("truth_stats requires 'mean'")
    s = float(sim_stats["mean"])
    t = float(truth_stats["mean"])
    diff = abs(s - t)
    # 单点：spearman 不定义 -> 约定 1.0 当差距小，否则按 fidelity 反映
    spear = 1.0
    rmse = diff
    eucl = diff
    fid = _fidelity_from_rmse(rmse)
    return FidelityReport(spearman=spear, rmse=rmse, euclidean=eucl,
                          fidelity_score=fid,
                          notes=[f"compared on 'mean' only (sim={s}, truth={t})"])


def calibrate(report: AggregateReport, ground_truth: dict) -> FidelityReport:
    """按 report.kind 路由到对应校准器。"""
    if report.n_total == 0:
        raise ValueError("cannot calibrate empty AggregateReport")
    if report.n_valid == 0:
        raise ValueError("cannot calibrate: no valid samples in report")
    if report.kind is DecisionKind.CHOOSE:
        return calibrate_categorical(report.stats.get("share", {}),
                                     ground_truth)
    # 其它皆视为数值
    return calibrate_numeric(report.stats, ground_truth)
