# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""构建合成个体池 → 输出联合分布 content JSON(内置 seed)。

维度:年龄×性别×学历×婚姻×职业(全国真联合,IPF) + 家庭规模/省份(弱耦合边际)。
含验证门禁:age×sex×marriage 留出重建 TVD 超阈值则非零退出。
用法:python -m tools.synthpop.build_pool [out.json]
"""
from __future__ import annotations

import json
import sys

import numpy as np

from tools.synthpop import categories as C
from tools.synthpop.ipf import ipf
from tools.synthpop.read_tables import (read_age_sex_edu, read_age_sex_occ,
                                        read_age_sex_edu_marriage)
from tools.synthpop.validate import validate_age_sex_marriage

POOL_SIZE = 12000
TVD_GATE = 0.02
RNG = np.random.default_rng(20200101)

# 省份占比(cn_census_2020,弱耦合边际)
PROV_W = {
    "广东": 0.0893, "山东": 0.0719, "河南": 0.0704, "江苏": 0.0600,
    "四川": 0.0593, "河北": 0.0528, "湖南": 0.0471, "浙江": 0.0457,
    "安徽": 0.0432, "湖北": 0.0409, "广西": 0.0355, "云南": 0.0334,
    "江西": 0.0320, "辽宁": 0.0302, "福建": 0.0294, "陕西": 0.0280,
    "贵州": 0.0273, "山西": 0.0247, "重庆": 0.0227, "黑龙江": 0.0226,
    "新疆": 0.0183, "甘肃": 0.0177, "上海": 0.0176, "吉林": 0.0171,
    "内蒙古": 0.0170, "北京": 0.0155, "天津": 0.0098, "海南": 0.0071,
    "宁夏": 0.0051, "青海": 0.0042, "西藏": 0.0026,
}
# 家庭规模占比(jiating 全国家庭户规模总表,1~7+ 人户)
HSIZE_W = {
    "一人户": 0.2542, "二人户": 0.2972, "三人户": 0.2101, "四人户": 0.1319,
    "五人户": 0.0618, "六人户": 0.0306, "七人及以上户": 0.0142,
}


def build_joint():
    """5 维联合 age×sex×edu×marriage×occ(归一) + IPF report。"""
    e = read_age_sex_edu()              # [A,2,E]
    o = read_age_sex_occ()             # [A,2,O]
    m = read_age_sex_edu_marriage()    # [A,2,M]
    A, S, E = e.shape
    O = o.shape[2]
    M = m.shape[2]
    ase = e / e.sum()                  # axes (0,1,2) age×sex×edu
    asm = m / m.sum()                  # axes (0,1,3) age×sex×mar
    aso = o / o.sum()                  # axes (0,1,4) age×sex×occ
    shape = (A, S, E, M, O)
    joint, rep = ipf(shape, [((0, 1, 2), ase), ((0, 1, 3), asm),
                             ((0, 1, 4), aso)], max_iter=400, tol=1e-9)
    return joint, rep


def _weighted_keys(d):
    ks = list(d); ws = np.array([d[k] for k in ks], dtype=float)
    return ks, ws / ws.sum()


def build_content():
    # --- 验证门禁 ---
    v = validate_age_sex_marriage()
    if (not v["converged"]) or v["tv_ipf"] > TVD_GATE:
        raise SystemExit(
            f"验证未过: TVD={v['tv_ipf']:.4f} (阈值{TVD_GATE}), "
            f"收敛={v['converged']} — 不产出 JSON")

    joint, rep = build_joint()
    A, S, E, M, O = joint.shape

    # --- 从联合抽个体池 ---
    flat = joint.flatten()
    flat = flat / flat.sum()
    idx = RNG.choice(len(flat), size=POOL_SIZE, p=flat)
    coords = np.array(np.unravel_index(idx, joint.shape)).T  # [N,5]
    prov_k, prov_p = _weighted_keys(PROV_W)
    hs_k, hs_p = _weighted_keys(HSIZE_W)
    prov_idx = RNG.choice(len(prov_k), size=POOL_SIZE, p=prov_p)
    hs_idx = RNG.choice(len(hs_k), size=POOL_SIZE, p=hs_p)

    # 维度定义(顺序与 members 编码一致)
    dims = [
        {"key": {"zh": "年龄段", "en": "age band"},
         "categories": C.bilingual(C.AGE_BANDS), "coupling": "joint"},
        {"key": {"zh": "性别", "en": "gender"},
         "categories": C.bilingual(C.SEX), "coupling": "joint"},
        {"key": {"zh": "学历", "en": "education"},
         "categories": C.bilingual(C.EDU), "coupling": "joint"},
        {"key": {"zh": "婚姻状态", "en": "marital status"},
         "categories": C.bilingual(C.MARRIAGE), "coupling": "joint"},
        {"key": {"zh": "职业", "en": "occupation"},
         "categories": C.bilingual(C.OCCUPATION), "coupling": "joint"},
        {"key": {"zh": "家庭规模", "en": "household size"},
         "categories": C.bilingual(C.HOUSEHOLD_SIZE), "coupling": "marginal"},
        {"key": {"zh": "省份", "en": "province"},
         "categories": C.bilingual(C.PROVINCE), "coupling": "marginal",
         "conditioned_on": []},
    ]
    # 每个个体 = 一户(1 member);members 编码 = 7 维索引
    households = []
    for i in range(POOL_SIZE):
        a, s, ed, mar, occ = (int(x) for x in coords[i])
        rec = [a, s, ed, mar, occ, int(hs_idx[i]), int(prov_idx[i])]
        households.append({"weight": 1.0, "members": [rec]})

    content = {
        "name": {"zh": "中国全国联合分布(IPF) 2020",
                 "en": "China National Joint (IPF) 2020"},
        # 兼容:也给边际(供展示/旧路径回退),从 joint 边际化
        "demographic": _marginals_block(joint, dims),
        "joint": {
            "version": 1, "method": "ipf", "level": "national",
            "dimensions": dims,
            "households": households,
            "provenance": {
                "seed_tables": ["B0503", "B0407", "B0403", "jiating"],
                "marginal_tables": ["province(cn_census_2020)",
                                    "household_size(jiating)"],
                "ipf_iterations": rep.iterations,
                "converged": bool(rep.converged),
                "pool_size": POOL_SIZE,
                "validation": {
                    "tv_distance": round(v["tv_ipf"], 4),
                    "tv_independent": round(v["tv_indep"], 4),
                    "error_reduction_pct": round(v["error_reduction"], 1),
                },
                "notes": [
                    "年龄×性别×学历×婚姻×职业 为全国真联合(IPF over 七普长表)",
                    "省份、家庭规模为弱耦合边际(独立挂载,非真联合)",
                    "就业相关维度(学历/职业)源于就业人口口径",
                ],
            },
        },
    }
    return content


def _marginals_block(joint, dims):
    """从 5 维 joint 导出前 5 维的边际,做成 Plan-B demographic(展示/回退用)。"""
    out = []
    axis_map = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4}  # joint 轴
    for di in range(5):
        other = tuple(a for a in range(joint.ndim) if a != axis_map[di])
        marg = joint.sum(axis=other)
        cats = dims[di]["categories"]
        values = [{"label": cats[k], "weight": float(marg[k])}
                  for k in range(len(cats))]
        out.append({"name": dims[di]["key"],
                    "distribution": {"values": values}})
    return out


if __name__ == "__main__":
    content = build_content()
    out = sys.argv[1] if len(sys.argv) > 1 else \
        "wanxiang/datasources/distributions/cn_national_joint_2020.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(content, f, ensure_ascii=False, separators=(",", ":"))
    import os
    print("written %s (%.0f KB)" % (out, os.path.getsize(out) / 1024))
    pv = content["joint"]["provenance"]["validation"]
    print("validation TVD=%.4f error_reduction=%.1f%%" % (
        pv["tv_distance"], pv["error_reduction_pct"]))
    print("pool=%d households" % len(content["joint"]["households"]))
