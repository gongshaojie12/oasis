# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""离线读七普 .xls 交叉表 → 归一到规范类目的 numpy 计数矩阵。

表结构(已核查):第0列分 [总计 block, 男 block, 女 block],每 block 内是
年龄段行;数据列是各类目(学历/职业/婚姻)。我们丢弃"总计"block,只用
男/女两个 block 得到 age×sex×category 三维计数。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from tools.synthpop import categories as C

DATA = "docs/persons"


def _num(x) -> float:
    try:
        v = float(x)
        return v if v == v else 0.0
    except (TypeError, ValueError):
        return 0.0


def _sex_blocks(df, col0_start=5):
    """返回 {'男': {age_idx: rowidx}, '女': {...}}。"""
    blocks = {"男": {}, "女": {}}
    cur = None
    for i in range(col0_start, len(df)):
        c0 = str(df.iloc[i, 0]).strip()
        if c0 in ("男", "女"):
            cur = c0
            continue
        if c0 in ("总  计", "总计", "合计"):
            cur = None
            continue
        if cur is not None and c0 and c0 != "nan":
            ai = C.age_to_index(c0)
            if ai is not None:
                # 同一统一年龄段可能被多个源行累加(如 75+/80-84/85+)
                blocks[cur].setdefault(ai, []).append(i)
    return blocks


def read_age_sex_edu():
    """B0403 → age×sex×edu 计数 [13,2,6]。"""
    df = pd.read_excel(f"{DATA}/jiuye/B0403.xls", header=None)
    # 列: 1=合计 2=未上过学 3=学前 4=小学 5=初中 6=高中 7=大专 8=本科 9=硕士 10=博士
    # 归并到 6 档 EDU: 未上过学(2+3) 小学(4) 初中(5) 高中(6) 大专(7) 本科+(8+9+10)
    edu_map = {0: [2, 3], 1: [4], 2: [5], 3: [6], 4: [7], 5: [8, 9, 10]}
    out = np.zeros((len(C.AGE_BANDS), 2, len(C.EDU)))
    blocks = _sex_blocks(df)
    for si, sx in enumerate(("男", "女")):
        for ai, rows in blocks[sx].items():
            for r in rows:
                for ei, cols in edu_map.items():
                    out[ai, si, ei] += sum(_num(df.iloc[r, c]) for c in cols)
    return out


def read_age_sex_occ():
    """B0407 → age×sex×occupation 计数 [13,2,7]。"""
    df = pd.read_excel(f"{DATA}/jiuye/B0407.xls", header=None)
    occ_cols = [2, 9, 21, 25, 41, 48, 81]  # 7 大类的'小计'列(已核查)
    out = np.zeros((len(C.AGE_BANDS), 2, len(C.OCCUPATION)))
    blocks = _sex_blocks(df, col0_start=9)
    for si, sx in enumerate(("男", "女")):
        for ai, rows in blocks[sx].items():
            for r in rows:
                for oi, c in enumerate(occ_cols):
                    out[ai, si, oi] += _num(df.iloc[r, c])
    return out


def read_age_sex_edu_marriage():
    """B0503 → age×sex×edu×marriage 真值四维(IPF 锚 + 验证用)。

    B0503 列结构(已核查):合计,男,女 | 未婚(小计,男,女) | 有配偶(...) |
    离婚(...) | 丧偶(...)。但行是 年龄组(总计/各年龄),其下又分学历?
    实际 B0503 行 = 年龄(大组)→ 各学历;需逐行判断。为稳健,这里只取
    age×sex×marriage(三维,把学历汇总),作为 IPF 的 age×marriage 约束来源。
    """
    df = pd.read_excel(f"{DATA}/hunyin/B0503.xls", header=None)
    male = {0: 5, 1: 8, 2: 11, 3: 14}    # marriage idx -> 男列
    female = {0: 6, 1: 9, 2: 12, 3: 15}  # marriage idx -> 女列
    out = np.zeros((len(C.AGE_BANDS), 2, len(C.MARRIAGE)))
    for i in range(len(df)):
        c0 = str(df.iloc[i, 0]).strip()
        ai = C.age_to_index(c0)
        if ai is None:
            continue
        r = df.iloc[i].tolist()
        for mi in range(4):
            out[ai, 0, mi] += _num(r[male[mi]])
            out[ai, 1, mi] += _num(r[female[mi]])
    return out


if __name__ == "__main__":
    e = read_age_sex_edu()
    o = read_age_sex_occ()
    m = read_age_sex_edu_marriage()
    print("age×sex×edu  sum=%.0f shape=%s" % (e.sum(), e.shape))
    print("age×sex×occ  sum=%.0f shape=%s" % (o.sum(), o.shape))
    print("age×sex×mar  sum=%.0f shape=%s" % (m.sum(), m.shape))
    # sanity: 性别比例
    print("edu表 男占比 %.3f" % (e[:, 0, :].sum() / e.sum()))
    print("mar表 男占比 %.3f" % (m[:, 0, :].sum() / m.sum()))
