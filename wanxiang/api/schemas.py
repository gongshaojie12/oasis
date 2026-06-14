# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""Pydantic v2 请求/响应模型。"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

DecisionKindStr = Literal["rate", "choose", "click_probability",
                          "sentiment", "willingness_to_pay"]


class ScenarioPayload(BaseModel):
    material: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1)
    kind: DecisionKindStr
    options: list[str] | None = None

    @model_validator(mode="after")
    def _choose_needs_options(self):
        if self.kind == "choose" and not self.options:
            raise ValueError("kind='choose' requires non-empty options list")
        return self


class ModelConfig(BaseModel):
    provider: Literal["stub", "deepseek"]
    api_key: str | None = None
    model_name: str | None = None

    @model_validator(mode="after")
    def _deepseek_needs_key(self):
        if self.provider == "deepseek" and not self.api_key:
            raise ValueError("provider='deepseek' requires api_key")
        return self


class SimulateRequest(BaseModel):
    distribution_path: str
    n: int = Field(..., gt=0, le=100_000)
    seed: int = 42
    scenario: ScenarioPayload
    rounds: int = Field(0, ge=0, le=10)
    concurrency: int = Field(16, ge=1, le=128)
    model: ModelConfig
    # L3 平台方言名（如 "wechat" / "douyin"），可选；仅在 rounds>0 生效
    platform: str | None = None


class SimulateResponse(BaseModel):
    decision_kind: str
    n_total: int
    n_valid: int
    error_count: int
    error_rate: float
    report: dict[str, Any]
    markdown: str
    elapsed_ms: int
