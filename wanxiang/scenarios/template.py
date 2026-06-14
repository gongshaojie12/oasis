# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""ScenarioTemplate: 把领域场景固化为带变量的 yaml，让客户照填空使用。

YAML 结构（P5 起支持双语；保留向后兼容的纯字符串写法）::

    id: marketing_ad_ab_test
    name:
      zh: 营销创意 A/B 测试
      en: Marketing Creative A/B Test
    description:
      zh: ...
      en: ...
    decision_kind: rate            # rate/choose/click_probability/sentiment/willingness_to_pay
    material_template:
      zh: |
        新品 {product_name}，主打卖点：{value_prop}
      en: |
        New product {product_name}, key selling point: {value_prop}
    question_template:
      zh: 给出 0-10 的购买意愿评分
      en: Rate purchase intent on a 0-10 scale.
    variables:
      - name:
          zh: 产品名
          en: product name
        type: text
        required: true
    default_options:
      zh: [青提, 白桃]
      en: [Green Grape, White Peach]

旧的纯字符串字段也继续被接受，会被自动提升为 ``{zh: <str>, en: <str>}``。
``instantiate(template, values, locale="en")`` 选择对应语言渲染。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import yaml

from wanxiang.simulation.scenario import DecisionKind

_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

_SUPPORTED_LOCALES = ("zh", "en")
_DEFAULT_LOCALE = "zh"


def _localize_text(raw: Any) -> dict[str, str]:
    """str | dict | None → {zh: str, en: str}.

    Missing side falls back to the other; empty input → empty strings.
    """
    if isinstance(raw, dict):
        zh = raw.get("zh")
        en = raw.get("en")
        if zh is None:
            zh = en if en is not None else ""
        if en is None:
            en = zh if zh is not None else ""
        return {"zh": str(zh), "en": str(en)}
    if raw is None:
        return {"zh": "", "en": ""}
    s = str(raw)
    return {"zh": s, "en": s}


def _pick(field_dict: dict[str, str], locale: str) -> str:
    """Pick locale-specific text from a bilingual field; fall back to zh."""
    if not isinstance(field_dict, dict):
        return str(field_dict)
    if locale in field_dict and field_dict[locale]:
        return field_dict[locale]
    return field_dict.get(_DEFAULT_LOCALE) or field_dict.get("en") or ""


def _localize_variable(v: dict) -> dict:
    """Normalize a variable dict so ``name`` is bilingual.

    Returns a fresh dict (does not mutate input).
    """
    if not isinstance(v, dict):
        return v
    out = dict(v)
    if "name" in out:
        raw_name = out["name"]
        if isinstance(raw_name, dict):
            # bilingual name dict — keep zh as the canonical lookup key but
            # also expose the bilingual dict via "_label" for UIs.
            bil = _localize_text(raw_name)
            # The variable's `name` continues to be a plain string (used as
            # placeholder key in template); we prefer the zh side because
            # template authors typically write {zh_name} in material_template.
            out["name"] = bil["zh"]
            out["_label"] = bil
        else:
            out["name"] = str(raw_name)
            out["_label"] = {"zh": str(raw_name), "en": str(raw_name)}
    if "label" in out:
        out["label"] = _localize_text(out["label"])
    return out


def _localize_default_options(opts: Any) -> dict[str, list[str]] | None:
    """default_options may be: None | list | {zh: [...], en: [...]} →
    canonical {zh: [...], en: [...]} or None."""
    if opts is None:
        return None
    if isinstance(opts, dict):
        zh = list(opts.get("zh") or [])
        en = list(opts.get("en") or zh)
        if not zh and en:
            zh = list(en)
        return {"zh": zh, "en": en}
    if isinstance(opts, list):
        flat = [str(x) for x in opts]
        return {"zh": flat, "en": list(flat)}
    return None


@dataclass(frozen=True)
class ScenarioTemplate:
    id: str
    # Bilingual fields (always dicts with {"zh", "en"} keys after _build).
    name: dict[str, str]
    description: dict[str, str]
    decision_kind: DecisionKind
    material_template: dict[str, str]
    question_template: dict[str, str]
    variables: tuple[dict, ...] = field(default_factory=tuple)
    # default_options is either None or {"zh": [...], "en": [...]}.
    default_options: dict[str, list[str]] | None = None


def _build(raw: dict) -> ScenarioTemplate:
    variables = tuple(
        _localize_variable(v) for v in (raw.get("variables") or ())
    )
    return ScenarioTemplate(
        id=raw["id"],
        name=_localize_text(raw.get("name", raw["id"])),
        description=_localize_text(raw.get("description", "")),
        decision_kind=DecisionKind(raw["decision_kind"]),
        material_template=_localize_text(raw.get("material_template", "")),
        question_template=_localize_text(raw.get("question_template", "")),
        variables=variables,
        default_options=_localize_default_options(raw.get("default_options")),
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
    *,
    locale: str = _DEFAULT_LOCALE,
) -> dict[str, Any]:
    """把模板中的 {var} 替换为 values；返回可喂给 /v1/simulate 的 dict。

    P5: ``locale="en"`` 选择英文模板渲染；缺失时回退 zh。
    """
    if locale not in _SUPPORTED_LOCALES:
        locale = _DEFAULT_LOCALE
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

    material = _pick(template.material_template, locale).format(**filled_values)
    question = _pick(template.question_template, locale).format(**filled_values)

    payload: dict[str, Any] = {
        "material": material,
        "question": question,
        "kind": template.decision_kind.value,
    }
    if template.decision_kind is DecisionKind.CHOOSE:
        if options:
            payload["options"] = list(options)
        else:
            defaults = template.default_options or {}
            opt_list = defaults.get(locale) or defaults.get(_DEFAULT_LOCALE) or []
            payload["options"] = list(opt_list)
    else:
        payload["options"] = None
    return payload
