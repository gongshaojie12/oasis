# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""M1 输入侧合规(spec §M1 D11):画像入库前的差分隐私 / PII 扫描 / 合成补缺。

注意:这与现有 ``compliance/`` 的**输出侧** DP/PII(模拟结果脱敏)是两条路,
互不冲突。此处作用在**数据接入**环节:
- ``apply_input_dp``:给分布权重加 Laplace 噪声(防止小样本反推个体)。
- ``scan_pii``:扫描 value 标签里的个人可识别信息,只告警不阻断。
- ``synthetic_fill``:缺失的 group 用 SyntheticSource 补默认估计。
"""
from __future__ import annotations

import random

from wanxiang.compliance.dp import laplace_noise
from wanxiang.compliance.pii import find_pii
from wanxiang.personas.data_sources import (DistributionProfile,
                                            SyntheticSource, merge_profiles)


def apply_input_dp(profile: DistributionProfile, *, epsilon: float,
                   rng: random.Random | None = None) -> DistributionProfile:
    """给每个 trait 的权重加 Laplace 噪声并重新裁剪为正。

    epsilon 越小噪声越大。权重加噪后 clamp 到 [1e-6, +inf),保持可抽样。
    sensitivity 取 1.0(权重通常已归一到 0~1 量级)。
    """
    if epsilon <= 0:
        raise ValueError(f"epsilon must be > 0, got {epsilon}")
    rng = rng or random.Random()
    scale = 1.0 / epsilon
    content = dict(profile.content)
    for group in ("demographic", "personality", "media"):
        traits = content.get(group)
        if not isinstance(traits, list):
            continue
        new_traits = []
        for t in traits:
            vals = (t.get("distribution") or {}).get("values") or []
            new_vals = []
            for v in vals:
                w = v.get("weight", 0.0)
                try:
                    noisy = float(w) + laplace_noise(scale, rng=rng)
                except (TypeError, ValueError):
                    noisy = float(w) if isinstance(w, (int, float)) else 0.0
                new_vals.append({**v, "weight": max(1e-6, noisy)})
            new_traits.append({**t,
                               "distribution": {"values": new_vals}})
        content[group] = new_traits
    return DistributionProfile(
        content=content, name=profile.name, source_type=profile.source_type,
        notes=profile.notes + [f"已加差分隐私噪声(ε={epsilon})"])


def scan_pii(profile: DistributionProfile) -> list[str]:
    """扫描 trait name + value 标签里的 PII,返回告警列表(不修改数据)。"""
    warnings: list[str] = []
    for group in ("demographic", "personality", "media"):
        traits = profile.content.get(group) or []
        for t in traits:
            for field_text in _iter_label_texts(t):
                hits = find_pii(field_text)
                if hits:
                    kinds = ",".join(sorted({h.kind for h in hits}))
                    warnings.append(f"{group}: '{field_text}' 含疑似 PII({kinds})")
    return warnings


def _iter_label_texts(trait: dict):
    nm = trait.get("name")
    if isinstance(nm, dict):
        for x in nm.values():
            if isinstance(x, str):
                yield x
    elif isinstance(nm, str):
        yield nm
    for v in (trait.get("distribution") or {}).get("values") or []:
        lbl = v.get("label")
        if isinstance(lbl, dict):
            for x in lbl.values():
                if isinstance(x, str):
                    yield x
        elif isinstance(lbl, str):
            yield lbl


def synthetic_fill(profile: DistributionProfile) -> DistributionProfile:
    """缺失的 personality/media group 用 SyntheticSource 默认估计补齐。"""
    missing = [g for g in ("personality", "media")
               if not profile.content.get(g)]
    if not missing:
        return profile
    syn = SyntheticSource().load()
    # 只取缺的 group
    syn.content = {g: syn.content.get(g, []) for g in missing}
    merged = merge_profiles(profile, syn)
    merged.notes = profile.notes + [
        f"已合成补缺: {', '.join(missing)}(占位估计,非真实数据)"]
    merged.source_type = profile.source_type
    merged.name = profile.name
    return merged


__all__ = ["apply_input_dp", "scan_pii", "synthetic_fill"]
