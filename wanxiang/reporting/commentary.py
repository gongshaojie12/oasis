# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""M6+: LLM 自然语言解读 (commentary)。

把 report dict（aggregate + factors + counterfactuals + rejection + trajectory）
喂给 model_call，要一段 150-250 字的中文执行摘要。

设计：
- 提示词全部中文，与产品语言一致；
- 给模型结构化数据 + 明确字数限制 + 输出格式要求（散文，无 JSON）；
- model_call 接 [{role, content}] → str；不解析返回，原样回。
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable

ModelCall = Callable[[list[dict]], Awaitable[str]]


_SYSTEM = ("你是一名资深市场研究分析师，擅长把复杂的群体行为模拟数据"
            "转译成业务可读的执行摘要。语言：简体中文。"
            "输出风格：结论先行、洞察驱动、不复述数据。")


def _fmt_recommendation(rec: dict[str, Any], kind: str) -> str:
    if kind == "choose":
        top = rec.get("top")
        share = rec.get("share")
        if isinstance(share, (int, float)):
            return f"群体首选：{top}（份额 {share * 100:.1f}%）"
        return f"群体首选：{top}"
    mean = rec.get("mean")
    band = rec.get("confidence_band")
    rng = rec.get("range")
    parts = []
    if mean is not None:
        parts.append(f"群体均值 {mean:.2f}")
    if band and band[0] is not None and band[1] is not None:
        parts.append(f"置信带 p25–p75 {band[0]}–{band[1]}")
    if rng and rng[0] is not None and rng[1] is not None:
        parts.append(f"范围 {rng[0]}–{rng[1]}")
    return "；".join(parts) if parts else "（数值未提供）"


def _fmt_causal(causal: dict[str, Any] | None) -> str:
    if not causal or not causal.get("contributions"):
        return "未做因果归因分析"
    top = causal["contributions"][0]
    return (f"最大影响因子：{top['factor_label']}"
            f"（移除后 Δ={top['delta']:+.2f}）")


def _fmt_counterfactual(cf: dict[str, Any] | None) -> str:
    if not cf or not cf.get("outcomes"):
        return "未做反事实推演"
    best = max(cf["outcomes"],
                key=lambda o: o.get("delta_vs_baseline") or float("-inf"))
    return (f"最优替代：{best['label']}（vs 基线 Δ={best['delta_vs_baseline']:+.2f}）")


def _fmt_rejection(rej: dict[str, Any] | None) -> str:
    if not rej or rej.get("total_rejected", 0) == 0:
        return ""
    buckets = rej.get("buckets") or {}
    top3 = list(buckets.items())[:3]
    if not top3:
        return ""
    parts = [f"{k}={v}" for k, v in top3]
    return ("主要劝退原因 top-3："
            + ", ".join(parts)
            + f"（被拒样本共 {rej['total_rejected']} 例）")


def _fmt_trajectory(traj: list[dict[str, Any]] | None) -> str:
    if not traj or len(traj) < 2:
        return ""
    first = traj[0]
    last = traj[-1]
    m0, mN = first.get("mean"), last.get("mean")
    if m0 is None or mN is None:
        return ""
    return (f"群体演化：从 round{first['round_idx']} 的均值 {m0:.2f} "
            f"到 round{last['round_idx']} 的均值 {mN:.2f}")


def _build_prompt(report: dict[str, Any]) -> str:
    sc = report.get("scenario") or {}
    kind = sc.get("decision_kind", "?")
    question = sc.get("question", "")
    material = sc.get("material", "")
    n_valid = report.get("n_valid", "?")
    n_total = report.get("n_total", "?")
    rec = report.get("recommendation") or {}

    lines = [
        "请基于以下模拟数据，用中文写一段 150-250 字的执行摘要。",
        "",
        "【场景】",
        f"- 决策类型：{kind}",
        f"- 研究问题：{question}",
        f"- 投放材料：{material}",
        f"- 样本量：{n_valid} / {n_total}",
        "",
        "【核心结果】",
        f"- {_fmt_recommendation(rec, kind)}",
        f"- {_fmt_causal(report.get('causal'))}",
        f"- {_fmt_counterfactual(report.get('counterfactual'))}",
    ]
    rej_line = _fmt_rejection(report.get("rejection_analysis"))
    if rej_line:
        lines.append(f"- 劝退分布：{rej_line}")
    traj_line = _fmt_trajectory(report.get("trajectory"))
    if traj_line:
        lines.append(f"- 群体演化趋势：{traj_line}")

    lines += [
        "",
        "【输出要求】",
        "- 150-250 字纯中文散文，不要 JSON、不要 markdown 列表",
        "- 结论先行，揭示业务洞察而非复述数字",
        "- 如有显著趋势/最强因子/最优替代，必须点出",
    ]
    return "\n".join(lines)


async def generate_commentary(
    report_dict: dict[str, Any],
    model_call: ModelCall,
) -> str:
    """生成一段中文执行摘要。返回模型原文（不做后处理）。"""
    user_prompt = _build_prompt(report_dict)
    messages = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": user_prompt},
    ]
    return await model_call(messages)
