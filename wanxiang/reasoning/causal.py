# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""因果归因：拿到基线场景与一组可移除的因子，跑对照实验。"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from wanxiang.personas.persona import Persona
from wanxiang.simulation.aggregate import aggregate, AggregateReport
from wanxiang.simulation.batch import BatchRunner
from wanxiang.simulation.decision import ModelCall
from wanxiang.simulation.scenario import DecisionKind, ScenarioConfig


@dataclass(frozen=True)
class Factor:
    id: str
    label: str
    snippet: str  # 从 material 里要"移除"的子串（替换为空）


@dataclass(frozen=True)
class FactorContribution:
    factor_id: str
    factor_label: str
    baseline_metric: float
    ablated_metric: float
    delta: float       # baseline - ablated（正 = 因子正向贡献）
    abs_delta: float
    rank: int


@dataclass(frozen=True)
class CausalReport:
    baseline_metric: float
    contributions: list[FactorContribution] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _metric_of(report: AggregateReport, top_option: Any = None) -> float:
    """统一从 AggregateReport 提取标量 metric。

    数值 kind → mean
    CHOOSE   → 给定 top_option 的 share（默认 None = 用 report 自己的 top）
    """
    if report.n_valid == 0:
        return 0.0
    if report.kind is DecisionKind.CHOOSE:
        share = report.stats.get("share", {})
        if top_option is None:
            top_option = report.stats.get("top")
        return float(share.get(top_option, 0.0))
    return float(report.stats.get("mean", 0.0))


async def analyze_factor_contributions(
    baseline_scenario: ScenarioConfig,
    factors: list[Factor],
    personas: list[Persona],
    model_call: ModelCall,
    runner: BatchRunner | None = None,
) -> CausalReport:
    runner = runner or BatchRunner(decision_concurrency=16)

    # 1) baseline
    base_results = await runner.run_all(personas, baseline_scenario, model_call)
    base_report = aggregate(base_results)
    base_top = base_report.stats.get("top") \
        if base_report.kind is DecisionKind.CHOOSE else None
    baseline_metric = _metric_of(base_report, top_option=base_top)

    notes: list[str] = []
    raw: list[FactorContribution] = []

    for f in factors:
        if f.snippet not in baseline_scenario.material:
            notes.append(f"snippet not in material: {f.id}")
            continue
        ablated_material = baseline_scenario.material.replace(f.snippet, "")
        ablated_scenario = replace(baseline_scenario, material=ablated_material)
        ablated_results = await runner.run_all(
            personas, ablated_scenario, model_call)
        ablated_report = aggregate(ablated_results)
        ablated_metric = _metric_of(ablated_report, top_option=base_top)
        delta = baseline_metric - ablated_metric
        raw.append(FactorContribution(
            factor_id=f.id, factor_label=f.label,
            baseline_metric=baseline_metric,
            ablated_metric=ablated_metric,
            delta=delta, abs_delta=abs(delta),
            rank=0,  # placeholder
        ))

    # 按 abs_delta 降序排名
    raw.sort(key=lambda x: x.abs_delta, reverse=True)
    contributions = [
        replace(c, rank=i + 1) for i, c in enumerate(raw)
    ]
    return CausalReport(baseline_metric=baseline_metric,
                         contributions=contributions, notes=notes)
