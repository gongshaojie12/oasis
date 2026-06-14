# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""Differential Privacy (M3-12) — Laplace mechanism for numeric aggregates.

For small-sample protection: add ε-DP noise to mean/quartiles before export.
"""
from __future__ import annotations

import math
import random


def laplace_noise(scale: float, *, rng: random.Random | None = None) -> float:
    """Sample Laplace(0, scale). scale = sensitivity / epsilon."""
    rng = rng or random.Random()
    u = rng.random() - 0.5
    return -scale * math.copysign(math.log(1 - 2 * abs(u)), u)


def apply_dp_to_aggregate(
    aggregate: dict,
    *,
    epsilon: float,
    sensitivity: float = 1.0,
    rng: random.Random | None = None,
) -> dict:
    """Add Laplace noise to numeric aggregate fields.

    Operates on a copy. Noise targets: mean, p25/p50/p75 (in quartiles dict).
    Skips fields that are None or non-numeric.
    `sensitivity` defaults to 1.0 (suitable for 0-10 / 0-1 rating scales where
    individual contribution ≤ 1 after averaging). Caller should adjust for kind.
    """
    if epsilon <= 0:
        raise ValueError(f"epsilon must be > 0, got {epsilon}")
    rng = rng or random.Random()
    scale = sensitivity / epsilon
    out = dict(aggregate)  # shallow copy

    def noise(x):
        return None if x is None else x + laplace_noise(scale, rng=rng)

    if "mean" in out:
        out["mean"] = noise(out["mean"])
    if isinstance(out.get("quartiles"), dict):
        q = dict(out["quartiles"])
        for k in ("p25", "p50", "p75"):
            if k in q:
                q[k] = noise(q[k])
        out["quartiles"] = q
    return out
