# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""PersonaBuilder: 从精确字典或加权分布造虚拟人。

分布字典格式（每个 group 内每个特质独立给候选 (value, weight)）：

    {
        "demographic": {"性别": [("男", 0.5), ("女", 0.5)], ...},
        "personality": {"价格敏感度": [(0.2, 0.3), (0.5, 0.4), (0.8, 0.3)], ...},
        "media":       {"小红书": [(0.0, 0.5), (0.7, 0.5)], ...},
    }

权重无需归一；按比例使用。`sample(..., seed=...)` 保证完全确定性。
"""
from __future__ import annotations

import random
from typing import Any

from wanxiang.personas.persona import Persona

_GROUP_NAMES = ("demographic", "personality", "media")


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
        distribution: dict[str, dict[str, list[tuple[Any, float]]]],
        n: int,
        seed: int,
        name_prefix: str | None = None,
    ) -> list[Persona]:
        """按各维度独立分布抽样造 N 个 Persona。

        ID 从 0 起递增；name 默认形如 'agent#0' 或 '<prefix>#0'。
        """
        rng = random.Random(seed)
        prepared: dict[str, dict[str, tuple[list[Any], list[float]]]] = {}
        for group in _GROUP_NAMES:
            grp_dist = distribution.get(group, {}) or {}
            prepared[group] = {}
            for trait, choices in grp_dist.items():
                values = [v for v, _ in choices]
                weights = [w for _, w in choices]
                prepared[group][trait] = (values, weights)

        personas: list[Persona] = []
        for i in range(n):
            traits: dict[str, dict[str, Any]] = {g: {} for g in _GROUP_NAMES}
            for group, traits_map in prepared.items():
                for trait, (values, weights) in traits_map.items():
                    picked = rng.choices(values, weights=weights, k=1)[0]
                    traits[group][trait] = picked
            label = name_prefix if name_prefix is not None else "agent"
            personas.append(
                Persona(
                    agent_id=i,
                    name=f"{label}#{i}",
                    demographic=traits["demographic"],
                    personality=traits["personality"],
                    media=traits["media"],
                ))
        return personas
