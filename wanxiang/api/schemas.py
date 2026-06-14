# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""Pydantic v2 请求/响应模型。"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

DecisionKindStr = Literal["rate", "choose", "click_probability",
                          "sentiment", "willingness_to_pay"]


class MediaItemPayload(BaseModel):
    """M4: 单条媒体内容条目（HTTP 入参）。"""
    item_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    body: str = ""
    channel: str = ""
    tags: list[str] = Field(default_factory=list)
    author: str | None = None


class ScenarioPayload(BaseModel):
    material: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1)
    kind: DecisionKindStr
    options: list[str] | None = None
    # M4 MVP: 动态信息流
    media_pool: list[MediaItemPayload] = Field(default_factory=list)
    feed_k: int = Field(0, ge=0, le=50)

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


class CompliancePolicy(BaseModel):
    """M3-12 合规策略（可选）。所有字段默认 no-op。"""
    redact_pii: bool = False           # 报告所有字符串叶子做 PII 脱敏
    dp_epsilon: float | None = None    # 若设，对聚合数值加 Laplace 噪声
    dp_sensitivity: float = 1.0        # 个体贡献敏感度（默认 1.0）
    moderate_material: bool = False    # scenario.material 过预设审核器


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
    # M3-12 合规策略（可选；不传 → 行为不变）
    compliance: CompliancePolicy | None = None


class SimulateResponse(BaseModel):
    decision_kind: str
    n_total: int
    n_valid: int
    error_count: int
    error_rate: float
    report: dict[str, Any]
    markdown: str
    elapsed_ms: int


# ----- M5: 变量笛卡尔展开 -----

class SweepRequest(BaseModel):
    """笛卡尔积展开：variable_grid 内每个 key 是一个变量轴，value 是该轴的候选列表。

    例如 {"copy": ["A","B"], "channel": ["xhs","douyin"]} → 4 个组合。
    每个组合会把 scenario.material/question 中的 {copy}/{channel} 占位符替换。
    """
    distribution_path: str
    n: int = Field(..., ge=1, le=100_000)
    seed: int = 0
    scenario: ScenarioPayload       # material/question 可含 {var} 占位符
    rounds: int = Field(0, ge=0, le=10)
    platform: str | None = None
    model: ModelConfig
    variable_grid: dict[str, list[str]] = Field(
        ..., description="变量轴 → 候选值列表；笛卡尔积展开"
    )

    @field_validator("variable_grid")
    @classmethod
    def _grid_not_empty(cls, v):
        if not v:
            raise ValueError("variable_grid must have at least one axis")
        for axis, values in v.items():
            if not values:
                raise ValueError(f"axis {axis!r} has no values")
        return v


class SweepCombo(BaseModel):
    """单个组合的解析值 + (同步模式)结果引用。"""
    combo_id: str               # 例 "copy=A|channel=xhs"
    values: dict[str, str]      # 例 {"copy":"A","channel":"xhs"}
    task_id: str | None = None  # async: 子任务 id; sync: None
    result: dict | None = None  # sync: SimulateResponse.dict; async: None
    error: str | None = None    # sync: 该 combo 失败时的错误消息


class SweepResponse(BaseModel):
    total_combos: int
    combos: list[SweepCombo]
