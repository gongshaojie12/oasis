# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""M5: 变量笛卡尔展开 (sweep)。

笛卡尔积 grid 展开 + {var} 占位符替换。供 /v1/simulations/sweep 路由复用。
"""
from __future__ import annotations

from itertools import product

from wanxiang.api.schemas import SimulateRequest

# 最大组合数：保护服务端不被 grid × n 拖垮（spec §M5）
MAX_SWEEP_COMBOS = 100


def expand_grid(grid: dict[str, list[str]]) -> list[dict[str, str]]:
    """{a:[1,2], b:[x,y]} → [{a:1,b:x},{a:1,b:y},{a:2,b:x},{a:2,b:y}]。

    空 grid → [{}]（一个空 combo），便于上层"无变量也跑一次"语义。
    """
    if not grid:
        return [{}]
    axes = list(grid.keys())
    values_lists = [grid[a] for a in axes]
    combos: list[dict[str, str]] = []
    for values_tuple in product(*values_lists):
        combos.append(dict(zip(axes, values_tuple)))
    return combos


def combo_id(values: dict[str, str]) -> str:
    """稳定、人类可读的 ID：按轴名字母排序，'|' 分隔。"""
    return "|".join(f"{k}={v}" for k, v in sorted(values.items()))


class _SafeDict(dict):
    """缺失 key 时返回 '{key}'，让 str.format_map 不抛 KeyError。"""

    def __missing__(self, key):
        return "{" + key + "}"


def apply_combo(req: SimulateRequest, values: dict[str, str]) -> SimulateRequest:
    """把 {var} 占位符替换进 scenario.material 和 scenario.question。

    使用 str.format_map + _SafeDict：缺失 key 原样保留。
    返回 NEW SimulateRequest（不可变；不修改入参）。
    """
    safe = _SafeDict(values)

    sc = req.scenario.model_copy()
    sc.material = sc.material.format_map(safe)
    sc.question = sc.question.format_map(safe)

    new_req = req.model_copy()
    new_req.scenario = sc
    return new_req


__all__ = [
    "MAX_SWEEP_COMBOS",
    "expand_grid",
    "combo_id",
    "apply_combo",
]
