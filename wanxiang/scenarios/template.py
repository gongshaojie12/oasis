# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""ScenarioTemplate: 把领域场景固化为带变量的 yaml，让客户照填空使用。

YAML 结构：

    id: marketing_ad_ab_test
    name: 营销创意 A/B 测试
    description: ...
    decision_kind: rate            # rate/choose/click_probability/sentiment/willingness_to_pay
    material_template: |
      新品 {product_name}，主打卖点：{value_prop}
    question_template: |
      给出 0-10 的购买意愿评分
    variables:
      - name: product_name
        label: 新品名
        type: text
        required: true
      - name: value_prop
        label: 核心卖点
        type: text
        required: true
        default: ""
    default_options: null          # CHOOSE kind 时给出
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import yaml

from wanxiang.simulation.scenario import DecisionKind

_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")


@dataclass(frozen=True)
class ScenarioTemplate:
    id: str
    name: str
    description: str
    decision_kind: DecisionKind
    material_template: str
    question_template: str
    variables: tuple[dict, ...] = field(default_factory=tuple)
    default_options: tuple[str, ...] | None = None


def _build(raw: dict) -> ScenarioTemplate:
    opts = raw.get("default_options")
    return ScenarioTemplate(
        id=raw["id"],
        name=raw["name"],
        description=raw.get("description", ""),
        decision_kind=DecisionKind(raw["decision_kind"]),
        material_template=raw["material_template"],
        question_template=raw["question_template"],
        variables=tuple(raw.get("variables") or ()),
        default_options=tuple(opts) if opts else None,
    )


def load_template(name: str) -> ScenarioTemplate:
    path = os.path.join(_TEMPLATES_DIR, f"{name}.yaml")
    if not os.path.exists(path):
        raise FileNotFoundError(f"template not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return _build(raw)


def list_templates() -> list[ScenarioTemplate]:
    out: list[ScenarioTemplate] = []
    if not os.path.isdir(_TEMPLATES_DIR):
        return out
    for fname in sorted(os.listdir(_TEMPLATES_DIR)):
        if not fname.endswith(".yaml"):
            continue
        out.append(load_template(fname[:-5]))
    return out


def instantiate(
    template: ScenarioTemplate,
    values: dict[str, Any],
    options: list[str] | None = None,
) -> dict[str, Any]:
    """把模板中的 {var} 替换为 values；返回可喂给 /v1/simulate 的 dict。"""
    filled_values: dict[str, Any] = {}
    for v in template.variables:
        name = v["name"]
        if name in values:
            filled_values[name] = values[name]
        elif "default" in v and v["default"] is not None:
            filled_values[name] = v["default"]
        elif v.get("required", False):
            raise ValueError(f"missing required variable: {name}")
        else:
            filled_values[name] = ""

    material = template.material_template.format(**filled_values)
    question = template.question_template.format(**filled_values)

    payload: dict[str, Any] = {
        "material": material,
        "question": question,
        "kind": template.decision_kind.value,
    }
    if template.decision_kind is DecisionKind.CHOOSE:
        payload["options"] = list(options) if options else list(
            template.default_options or ())
    else:
        payload["options"] = None
    return payload
