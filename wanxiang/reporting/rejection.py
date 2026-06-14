# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""M6+: 劝退原因构成 (rejection reasons breakdown)。

对 CHOOSE/RATE/SENTIMENT/CLICK_PROBABILITY/WTP 等决策，统计"为什么没买
/为什么没选/为什么打低分"的原因分布。把每个被拒样本的 reasoning 文本
按关键词归桶。

输入：list[DecisionResult]。
- reasoning 文本来源：优先看 DecisionResult.reasoning 属性（如果未来扩展），
  否则从 raw 字段（模型原始 JSON）里解析 "reasoning" / "reason" / "explain"
  字段；都没有就把 raw 当文本看。

输出：{
  "total_rejected": N,
  "buckets": {bucket_name: count},   # 按 count 降序
  "examples": {bucket_name: [verbatim reasoning, up to 2]},
}
"""
from __future__ import annotations

import json
from typing import Any, Iterable

from wanxiang.simulation.decision import DecisionResult

# 中英双语关键词桶。新增桶 → 直接往这里加。匹配规则：substring + case-insensitive。
REJECTION_BUCKETS: dict[str, list[str]] = {
    "price_too_high": ["太贵", "价格高", "买不起", "偏贵", "贵了",
                       "expensive", "overpriced", "high price",
                       "too pricey", "costly"],
    "low_quality_concern": ["质量差", "假货", "做工", "质量不好", "粗糙",
                            "low quality", "shoddy", "poor quality",
                            "bad quality", "cheap looking"],
    "no_need": ["不需要", "用不上", "没必要", "用不到",
                "no need", "unnecessary", "don't need", "do not need"],
    "brand_distrust": ["不信任", "山寨", "没听过", "陌生品牌",
                       "untrustworthy", "no-name", "unknown brand",
                       "sketchy"],
    "competitor_preferred": ["其他更好", "我已经有", "替代品", "别的牌子更好",
                             "alternative", "competitor", "already have",
                             "prefer other"],
    "uncertainty": ["不确定", "再看看", "犹豫", "考虑一下", "再想想",
                    "uncertain", "wait and see", "not sure", "hesitant"],
}
DEFAULT_BUCKET = "other"


def bucket_reason(text: str) -> str:
    """把一段 reasoning 文本归到第一个匹配的桶。

    case-insensitive，substring 匹配。空串或没匹配 → DEFAULT_BUCKET。
    """
    if not text:
        return DEFAULT_BUCKET
    lowered = text.lower()
    for bucket, keywords in REJECTION_BUCKETS.items():
        for kw in keywords:
            if kw.lower() in lowered:
                return bucket
    return DEFAULT_BUCKET


def _extract_reasoning(r: DecisionResult) -> str:
    """从 DecisionResult 提取 reasoning 文本。

    优先序：
      1. r.reasoning 属性（若将来扩展）
      2. raw JSON 里的 reasoning / reason / explain 字段
      3. ""（不可用 → 跳过）
    """
    explicit = getattr(r, "reasoning", None)
    if isinstance(explicit, str) and explicit:
        return explicit
    raw = getattr(r, "raw", None)
    if not raw:
        return ""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError, TypeError):
        return ""
    if not isinstance(data, dict):
        return ""
    for key in ("reasoning", "reason", "explain", "explanation"):
        v = data.get(key)
        if isinstance(v, str) and v:
            return v
    return ""


def _is_rejected(r: DecisionResult, kind: str,
                 threshold: float | int | str | None) -> bool:
    """根据 kind + threshold 判断是否算"被拒"。"""
    val = r.value
    if val is None:
        return False
    if kind == "rate":
        t = 5 if threshold is None else float(threshold)
        try:
            return float(val) < t
        except (TypeError, ValueError):
            return False
    if kind == "sentiment":
        t = 0.0 if threshold is None else float(threshold)
        try:
            return float(val) < t
        except (TypeError, ValueError):
            return False
    if kind == "click_probability":
        t = 0.5 if threshold is None else float(threshold)
        try:
            return float(val) < t
        except (TypeError, ValueError):
            return False
    if kind == "willingness_to_pay" or kind == "wtp":
        # 数值型：threshold 必须显式（无默认）
        if threshold is None:
            return False
        try:
            return float(val) < float(threshold)
        except (TypeError, ValueError):
            return False
    if kind == "choose":
        # categorical：threshold = 获胜选项，其它都算被拒
        if threshold is None:
            return False
        return val != threshold
    if kind == "purchase_intent":
        # 兼容 spec 里提到的枚举：reject / no / unlikely 视为拒
        # 或者数值低于 threshold
        if isinstance(val, str):
            return val.lower() in {"reject", "no", "unlikely", "拒绝", "不会买"}
        if threshold is not None:
            try:
                return float(val) < float(threshold)
            except (TypeError, ValueError):
                return False
        return False
    return False


def analyze_rejection_reasons(
    results: Iterable[DecisionResult],
    kind: str,
    threshold: float | int | str | None = None,
) -> dict[str, Any]:
    """统计被拒样本的原因桶分布。"""
    items = list(results)
    buckets: dict[str, int] = {}
    examples: dict[str, list[str]] = {}
    total_rejected = 0

    for r in items:
        if r.error is not None:
            continue
        if not _is_rejected(r, kind, threshold):
            continue
        reason = _extract_reasoning(r)
        if not reason:
            # spec: skip empty reasoning
            continue
        total_rejected += 1
        b = bucket_reason(reason)
        buckets[b] = buckets.get(b, 0) + 1
        ex_list = examples.setdefault(b, [])
        if len(ex_list) < 2:
            ex_list.append(reason)

    # sort buckets desc by count（同 count 按 key 稳定）
    sorted_buckets = dict(
        sorted(buckets.items(), key=lambda kv: (-kv[1], kv[0])))

    return {
        "total_rejected": total_rejected,
        "buckets": sorted_buckets,
        "examples": {k: examples[k] for k in sorted_buckets},
    }
