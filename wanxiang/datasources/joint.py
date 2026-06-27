# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""联合分布(合成个体池)运行时 schema + 加载/抽样视图。

content 顶层可选 ``joint`` 块(由离线 tools/synthpop 产出),形如:
    {"version":1,"method":"ipf","level":"national",
     "dimensions":[{"key":{"zh","en"},"categories":[{"zh","en"}...],
                    "coupling":"joint"|"marginal"}...],
     "households":[{"weight":1.0,"members":[[i0,i1,...]]}...],
     "provenance":{...}}

members 里每个成员是各维类目的整数索引。运行时只**抽样**,不算 IPF。
依赖:stdlib only(bisect)。
"""
from __future__ import annotations

import bisect
from dataclasses import dataclass
from typing import Any


@dataclass
class JointView:
    dimensions: list[dict]          # 各维 {key:{zh,en}, categories:[{zh,en}], coupling}
    households: list[dict]          # [{weight, members:[[idx...]]}]
    _cum: list[float]               # 累积权重(供 bisect)
    provenance: dict

    def household_count(self) -> int:
        return len(self.households)

    def dim_label(self, di: int, locale: str) -> str:
        k = self.dimensions[di]["key"]
        return k.get(locale) or k.get("zh") or ""

    def cat_label(self, di: int, ci: int, locale: str) -> str:
        c = self.dimensions[di]["categories"][ci]
        if isinstance(c, dict):
            return c.get(locale) or c.get("zh") or ""
        return str(c)

    def pick_household(self, rng) -> dict:
        """按权重抽一户(rng 为 random.Random)。"""
        if not self.households:
            return {"members": []}
        r = rng.random() * self._cum[-1]
        i = bisect.bisect_right(self._cum, r)
        if i >= len(self.households):
            i = len(self.households) - 1
        return self.households[i]


def validate_joint(raw: dict) -> tuple[bool, list[str]]:
    """校验 joint 块。返回 (ok, errors)。raw 是含 'joint' 的 content。"""
    errors: list[str] = []
    j = raw.get("joint")
    if j is None:
        return True, []  # 无 joint 块 = 合法(走边际路径)
    if not isinstance(j, dict):
        return False, ["joint 必须是对象"]
    dims = j.get("dimensions")
    if not isinstance(dims, list) or not dims:
        errors.append("joint.dimensions 必须是非空列表")
        dims = dims if isinstance(dims, list) else []
    ndim = len(dims)
    for di, d in enumerate(dims):
        if not isinstance(d, dict) or "categories" not in d:
            errors.append(f"dimension[{di}] 缺 categories")
            continue
        if not d.get("categories"):
            errors.append(f"dimension[{di}] categories 为空")
    hh = j.get("households")
    if not isinstance(hh, list) or not hh:
        errors.append("joint.households 必须是非空列表")
        hh = hh if isinstance(hh, list) else []
    # 抽查前 50 户的成员编码合法性
    ncats = [len(d.get("categories", [])) for d in dims]
    for h in hh[:50]:
        for mem in h.get("members", []):
            if len(mem) != ndim:
                errors.append(f"成员编码长度 {len(mem)} != 维度数 {ndim}")
                break
            for di, ci in enumerate(mem):
                if not (isinstance(ci, int) and 0 <= ci < ncats[di]):
                    errors.append(f"成员维度{di}索引越界: {ci}")
                    break
    return (len(errors) == 0), errors[:20]


def load_joint_from_dict(raw: dict) -> JointView | None:
    """从 content dict 构建 JointView;无 joint 块或非法 → None。"""
    if not isinstance(raw, dict):
        return None
    j = raw.get("joint")
    if not isinstance(j, dict):
        return None
    dims = j.get("dimensions")
    hh = j.get("households")
    if not isinstance(dims, list) or not isinstance(hh, list) or not hh:
        return None
    cum: list[float] = []
    acc = 0.0
    for h in hh:
        w = h.get("weight", 1.0)
        try:
            acc += float(w)
        except (TypeError, ValueError):
            acc += 1.0
        cum.append(acc)
    return JointView(dimensions=dims, households=hh, _cum=cum,
                     provenance=j.get("provenance") or {})


def count_joint_dims(raw: dict) -> int:
    j = raw.get("joint") if isinstance(raw, dict) else None
    if isinstance(j, dict) and isinstance(j.get("dimensions"), list):
        return len(j["dimensions"])
    return 0


__all__ = ["JointView", "validate_joint", "load_joint_from_dict",
           "count_joint_dims"]
