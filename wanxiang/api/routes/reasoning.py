# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""POST /v1/causal & /v1/counterfactual —— M6 收官端点。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from wanxiang.api.auth import require_tenant
from wanxiang.api.deps import get_model_factory
from wanxiang.api.schemas import SimulateRequest
from wanxiang.api.tenancy import TenantInfo
from wanxiang.datasources import load_distribution
from wanxiang.personas import PersonaBuilder
from wanxiang.reasoning import (Alternative, Factor,
                                  analyze_factor_contributions,
                                  compare_alternatives)
from wanxiang.simulation.scenario import DecisionKind, ScenarioConfig

router = APIRouter()


class FactorPayload(BaseModel):
    id: str
    label: str
    snippet: str


class CausalRequest(BaseModel):
    baseline: SimulateRequest
    factors: list[FactorPayload]


class AlternativePayload(BaseModel):
    id: str
    label: str
    material_override: str | None = None
    question_override: str | None = None
    options_override: list[str] | None = None


class CounterfactualRequest(BaseModel):
    baseline: SimulateRequest
    baseline_label: str = "基线"
    alternatives: list[AlternativePayload]


def _build_scenario_and_personas(req: SimulateRequest):
    try:
        distribution = load_distribution(req.distribution_path)
    except FileNotFoundError as e:
        raise HTTPException(status_code=400,
                            detail=f"distribution file not found: {e}")
    pb = PersonaBuilder()
    personas = pb.sample(distribution, n=req.n, seed=req.seed)
    kind = DecisionKind(req.scenario.kind)
    # M4: 把 media_pool / feed_k 透传到 ScenarioConfig
    from wanxiang.api.routes.simulate import _media_pool_from_payload
    scenario = ScenarioConfig(
        material=req.scenario.material,
        question=req.scenario.question,
        decision_kind=kind,
        options=tuple(req.scenario.options) if req.scenario.options else None,
        media_pool=_media_pool_from_payload(req.scenario),
        feed_k=req.scenario.feed_k,
    )
    return scenario, personas


@router.post("/causal")
async def causal_endpoint(
    body: CausalRequest,
    model_factory=Depends(get_model_factory),
    tenant: TenantInfo = Depends(require_tenant),
):
    scenario, personas = _build_scenario_and_personas(body.baseline)
    model_call = model_factory(body.baseline.model)
    factors = [Factor(id=f.id, label=f.label, snippet=f.snippet)
               for f in body.factors]
    r = await analyze_factor_contributions(scenario, factors, personas,
                                             model_call)
    return {
        "baseline_metric": r.baseline_metric,
        "contributions": [
            {"factor_id": c.factor_id, "factor_label": c.factor_label,
             "baseline_metric": c.baseline_metric,
             "ablated_metric": c.ablated_metric,
             "delta": c.delta, "abs_delta": c.abs_delta, "rank": c.rank}
            for c in r.contributions],
        "notes": list(r.notes),
    }


@router.post("/counterfactual")
async def counterfactual_endpoint(
    body: CounterfactualRequest,
    model_factory=Depends(get_model_factory),
    tenant: TenantInfo = Depends(require_tenant),
):
    scenario, personas = _build_scenario_and_personas(body.baseline)
    model_call = model_factory(body.baseline.model)
    alts = [Alternative(
        id=a.id, label=a.label,
        material_override=a.material_override,
        question_override=a.question_override,
        options_override=tuple(a.options_override) if a.options_override else None)
        for a in body.alternatives]
    r = await compare_alternatives(
        (scenario, body.baseline_label), alts, personas, model_call)
    return {
        "baseline_label": r.baseline_label,
        "baseline_metric": r.baseline_metric,
        "outcomes": [
            {"alt_id": o.alt_id, "label": o.label, "metric": o.metric,
             "delta_vs_baseline": o.delta_vs_baseline}
            for o in r.outcomes],
    }
