# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""验证关:用真值三维表(age×sex×marriage)做留出重建,证明 IPF 优于独立。

方法:取真值 T(B0503 的 age×sex×marriage),只用它的两两边际跑 IPF 重建 R,
对比 TVD(R,T) vs TVD(独立假设,T)。error_reduction 越高越好(复刻 PoC 96.8%)。
"""
from __future__ import annotations

import numpy as np

from tools.synthpop.ipf import ipf
from tools.synthpop.read_tables import read_age_sex_edu_marriage


def tvd(a, b):
    return 0.5 * float(np.abs(a / a.sum() - b / b.sum()).sum())


def validate_age_sex_marriage():
    T = read_age_sex_edu_marriage()  # [age, sex, marriage] 计数
    Tn = T / T.sum()
    # 两两边际(模拟"只有交叉表"的情形)
    m_as = Tn.sum(axis=2)   # age×sex   axes (0,1)
    m_am = Tn.sum(axis=1)   # age×marriage axes (0,2)
    m_sm = Tn.sum(axis=0)   # sex×marriage axes (1,2)
    R, rep = ipf(Tn.shape, [((0, 1), m_as), ((0, 2), m_am), ((1, 2), m_sm)],
                 max_iter=500, tol=1e-10)
    # 独立基线
    p_a = Tn.sum(axis=(1, 2)); p_s = Tn.sum(axis=(0, 2))
    p_m = Tn.sum(axis=(0, 1))
    Indep = p_a[:, None, None] * p_s[None, :, None] * p_m[None, None, :]
    tv_ipf = tvd(R, Tn)
    tv_ind = tvd(Indep, Tn)
    er = (1 - tv_ipf / tv_ind) * 100 if tv_ind > 0 else 0.0
    return {
        "tv_ipf": tv_ipf, "tv_indep": tv_ind, "error_reduction": er,
        "iterations": rep.iterations, "converged": rep.converged,
    }


if __name__ == "__main__":
    r = validate_age_sex_marriage()
    print("=== IPF 留出重建验证(age×sex×marriage)===")
    print("独立基线 TVD : %.4f" % r["tv_indep"])
    print("IPF 重建 TVD : %.4f" % r["tv_ipf"])
    print("误差降低     : %.1f%%" % r["error_reduction"])
    print("迭代 %d 次, 收敛=%s" % (r["iterations"], r["converged"]))
