# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""反事实推演：给定基线 scenario 与 N 个替代方案，对比 metric。"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from wanxiang.personas.persona import Persona
from wanxiang.reasoning.causal import _metric_of  # 私有但本包内复用
from wanxiang.simulation.aggregate import aggregate
from wanxiang.simulation.batch import BatchRunner
from wanxiang.simulation.decision import ModelCall
from wanxiang.simulation.scenario import DecisionKind, ScenarioConfig


@dataclass(frozen=True)
class Alternative:
    id: str
    label: str
    material_override: str | None = None
    question_override: str | None = None
    options_override: tuple[str, ...] | None = None


@dataclass(frozen=True)
class AlternativeOutcome:
    alt_id: str
    label: str
    metric: float
    delta_vs_baseline: float


@dataclass(frozen=True)
class CounterfactualReport:
    baseline_label: str
    baseline_metric: float
    outcomes: list[AlternativeOutcome] = field(default_factory=list)


def _apply_overrides(base: ScenarioConfig, alt: Alternative) -> ScenarioConfig:
    kwargs = {}
    if alt.material_override is not None:
        kwargs["material"] = alt.material_override
    if alt.question_override is not None:
        kwargs["question"] = alt.question_override
    if alt.options_override is not None:
        kwargs["options"] = alt.options_override
    return replace(base, **kwargs) if kwargs else base


async def compare_alternatives(
    baseline: tuple[ScenarioConfig, str],
    alternatives: list[Alternative],
    personas: list[Persona],
    model_call: ModelCall,
    runner: BatchRunner | None = None,
) -> CounterfactualReport:
    base_sc, base_label = baseline
    runner = runner or BatchRunner(decision_concurrency=16)

    base_results = await runner.run_all(personas, base_sc, model_call)
    base_report = aggregate(base_results)
    base_top = base_report.stats.get("top") \
        if base_report.kind is DecisionKind.CHOOSE else None
    baseline_metric = _metric_of(base_report, top_option=base_top)

    outcomes: list[AlternativeOutcome] = []
    for alt in alternatives:
        sc = _apply_overrides(base_sc, alt)
        alt_results = await runner.run_all(personas, sc, model_call)
        alt_report = aggregate(alt_results)
        # 反事实里仍按基线 top 计算 share（让"哪个方案更接近原赢家"可比）
        metric = _metric_of(alt_report, top_option=base_top)
        outcomes.append(AlternativeOutcome(
            alt_id=alt.id, label=alt.label,
            metric=metric,
            delta_vs_baseline=metric - baseline_metric,
        ))

    return CounterfactualReport(
        baseline_label=base_label,
        baseline_metric=baseline_metric,
        outcomes=outcomes)
