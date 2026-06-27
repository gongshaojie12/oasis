# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""通用 IPF(迭代比例拟合)—— numpy only,无 scipy。

给定多个低阶边际(各自约束联合张量的某些轴),迭代缩放使联合的对应
边际匹配目标。返回归一联合 + 收敛报告。
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class IpfReport:
    iterations: int
    converged: bool
    max_residual: float


def ipf(shape, marginals, *, max_iter=500, tol=1e-8, seed_joint=None):
    """marginals: list of (axes_tuple, target_ndarray)。
    target 的形状 = 对应 axes 的维度(已归一为概率,sum=1)。
    返回 (joint_ndarray(sum=1), IpfReport)。"""
    X = np.ones(shape) if seed_joint is None else np.array(seed_joint,
                                                           dtype=float)
    X = np.clip(X, 1e-12, None)
    X /= X.sum()

    report = IpfReport(0, False, 1.0)
    for it in range(1, max_iter + 1):
        max_res = 0.0
        for axes, target in marginals:
            axes = tuple(axes)
            t = np.asarray(target, dtype=float)
            t = t / t.sum()
            other = tuple(a for a in range(X.ndim) if a not in axes)
            cur = X.sum(axis=other)
            # 残差
            max_res = max(max_res, float(np.abs(cur - t).max()))
            with np.errstate(divide="ignore", invalid="ignore"):
                ratio = np.where(cur > 0, t / cur, 0.0)
            # 把 ratio 广播回 X 的 ndim:在 other 轴插 1
            shp = [1] * X.ndim
            for k, a in enumerate(axes):
                shp[a] = t.shape[k]
            X = X * ratio.reshape(shp)
            X = np.clip(X, 1e-15, None)
        X /= X.sum()
        report.iterations = it
        report.max_residual = max_res
        if max_res < tol:
            report.converged = True
            break
    return X, report
