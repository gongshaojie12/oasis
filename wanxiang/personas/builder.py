# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""PersonaBuilder: 从精确字典或加权分布造虚拟人。

分布字典格式（每个 group 内每个特质独立给候选 (value, weight)）：

    {
        "demographic": {"性别": [("男", 0.5), ("女", 0.5)], ...},
        "personality": {"价格敏感度": [(0.2, 0.3), (0.5, 0.4), (0.8, 0.3)], ...},
        "media":       {"小红书": [(0.0, 0.5), (0.7, 0.5)], ...},
    }

权重无需归一；按比例使用。`sample(..., seed=...)` 保证完全确定性。

P5 双语：``sample(..., locale="en")`` 会把 trait key 与抽到的 value 都翻译为
英文（基于分布 YAML 内的 ``{zh, en}`` 元数据）。``locale="zh"`` 行为不变。
"""
from __future__ import annotations

import random
from typing import Any

from wanxiang.personas.persona import Persona

_GROUP_NAMES = ("demographic", "personality", "media")


def _prepare_group(group_view: Any, locale: str) -> list[tuple[str, list[Any], list[float]]]:
    """Yield (trait_name_localized, values_localized, weights) for sampling.

    Works for both new _TraitListView (P5 canonical) and legacy plain dict
    (e.g. test fixtures that pass {"trait": [(value, weight), ...]}).
    """
    out: list[tuple[str, list[Any], list[float]]] = []
    if group_view is None:
        return out

    # Path 1: new _TraitListView with bilingual meta available.
    if hasattr(group_view, "trait_meta"):
        for trait in group_view.trait_meta():
            name_dict = trait["name"]
            name = name_dict.get(locale) or name_dict.get("zh") or ""
            raw_values = trait.get("distribution", {}).get("values", []) or []
            values: list[Any] = []
            weights: list[float] = []
            for v in raw_values:
                label = v["label"]
                picked_label = label.get(locale) if isinstance(label, dict) else label
                if picked_label is None or picked_label == "":
                    picked_label = label.get("zh") if isinstance(label, dict) else label
                values.append(picked_label)
                weights.append(float(v["weight"]))
            out.append((name, values, weights))
        return out

    # Path 2: legacy dict {trait_name: [(value, weight), ...]}.
    if isinstance(group_view, dict):
        for trait, choices in group_view.items():
            values = [v for v, _ in choices]
            weights = [float(w) for _, w in choices]
            out.append((trait, values, weights))
    return out


class PersonaBuilder:

    def build(
        self,
        agent_id: int,
        name: str,
        demographic: dict[str, Any] | None = None,
        personality: dict[str, Any] | None = None,
        media: dict[str, Any] | None = None,
    ) -> Persona:
        """从精确字典造一个 Persona。"""
        return Persona(
            agent_id=agent_id,
            name=name,
            demographic=dict(demographic or {}),
            personality=dict(personality or {}),
            media=dict(media or {}),
        )

    def sample(
        self,
        distribution: dict[str, Any],
        n: int,
        seed: int,
        name_prefix: str | None = None,
        *,
        locale: str = "zh",
    ) -> list[Persona]:
        """按各维度独立分布抽样造 N 个 Persona。

        ID 从 0 起递增；name 默认形如 'agent#0' 或 '<prefix>#0'。

        P5: locale="en" 会用 yaml 中的 {zh, en} 元数据把 trait key 与抽到的
        value 双双翻译为英文；locale="zh"（默认）行为不变。
        """
        if locale not in ("zh", "en"):
            locale = "zh"
        rng = random.Random(seed)
        prepared: dict[str, list[tuple[str, list[Any], list[float]]]] = {}
        for group in _GROUP_NAMES:
            prepared[group] = _prepare_group(distribution.get(group), locale)

        personas: list[Persona] = []
        for i in range(n):
            traits: dict[str, dict[str, Any]] = {g: {} for g in _GROUP_NAMES}
            for group, trait_list in prepared.items():
                for trait_name, values, weights in trait_list:
                    if not values:
                        continue
                    picked = rng.choices(values, weights=weights, k=1)[0]
                    traits[group][trait_name] = picked
            label = name_prefix if name_prefix is not None else "agent"
            personas.append(
                Persona(
                    agent_id=i,
                    name=f"{label}#{i}",
                    demographic=traits["demographic"],
                    personality=traits["personality"],
                    media=traits["media"],
                    locale=locale,
                ))
        return personas
