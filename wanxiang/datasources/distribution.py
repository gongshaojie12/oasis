# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""YAML 分布加载器。

把人类友好的 YAML 格式（嵌套 dict）转换为 PersonaBuilder.sample()
期望的 `[(value, weight), ...]` 列表格式。

人口标签保留字符串；个性/媒体里"看起来像数字"的键被强制转为 float
（因为 YAML 里的纯数字键不允许，必须加引号写成字符串，但语义上是 float）。
"""
from __future__ import annotations

import os
from typing import Any

import yaml

_GROUPS = ("demographic", "personality", "media")


def _coerce_value(group: str, raw_key: Any) -> Any:
    if group == "demographic":
        return raw_key  # 保留原始类型（通常是字符串）
    # personality / media: 尝试转 float；不行就保留原值
    if isinstance(raw_key, str):
        try:
            return float(raw_key)
        except ValueError:
            return raw_key
    return raw_key


def load_distribution(path: str) -> dict[str, dict[str, list[tuple[Any, float]]]]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"distribution file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    out: dict[str, dict[str, list[tuple[Any, float]]]] = {
        g: {} for g in _GROUPS}
    for group in _GROUPS:
        group_data = raw.get(group) or {}
        for trait, choices in group_data.items():
            if not isinstance(choices, dict):
                raise ValueError(
                    f"trait {group!r}.{trait!r} must be a mapping of "
                    f"value -> weight, got {type(choices).__name__}")
            pairs: list[tuple[Any, float]] = []
            for k, w in choices.items():
                pairs.append((_coerce_value(group, k), float(w)))
            out[group][trait] = pairs
    return out
