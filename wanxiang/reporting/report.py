# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""把 AggregateReport (+ 可选 FidelityReport) 渲染为结构化 dict 与
人类可读 Markdown。dict 给 chat.html 工件卡用；Markdown 给 PDF/邮件
导出。
"""
from __future__ import annotations

from typing import Any

from wanxiang.calibration.fidelity import FidelityReport
from wanxiang.simulation.aggregate import AggregateReport
from wanxiang.simulation.scenario import DecisionKind, ScenarioConfig


def _fidelity_label(score: float) -> str:
    if score >= 0.85:
        return "高"
    if score >= 0.6:
        return "中"
    return "低"


def _fidelity_block(fidelity: FidelityReport) -> dict[str, Any]:
    return {
        "score": fidelity.fidelity_score,
        "label": _fidelity_label(fidelity.fidelity_score),
        "spearman": fidelity.spearman,
        "rmse": fidelity.rmse,
        "euclidean": fidelity.euclidean,
        "notes": list(fidelity.notes),
    }


def build_report(
    *,
    scenario: ScenarioConfig,
    aggregate: AggregateReport,
    persona_count: int,
    fidelity: FidelityReport | None = None,
    causal: Any = None,
    counterfactual: Any = None,
    rejection_analysis: dict[str, Any] | None = None,
    trajectory: list[dict[str, Any]] | list[Any] | None = None,
    commentary: str | None = None,
) -> dict[str, Any]:
    if aggregate.n_total == 0:
        raise ValueError("cannot report on empty AggregateReport")

    scenario_block = {
        "material": scenario.material,
        "question": scenario.question,
        "decision_kind": scenario.decision_kind.value,
        "options": list(scenario.options) if scenario.options else None,
    }

    # n_total > 0 但 n_valid == 0 的退化场景：仍然返回合法 dict，
    # 标记 no_valid_samples=True，让前端/渲染器走兜底分支而非崩溃。
    if aggregate.n_valid == 0:
        out: dict[str, Any] = {
            "scenario": scenario_block,
            "persona_count": persona_count,
            "n_total": aggregate.n_total,
            "n_valid": aggregate.n_valid,
            "error_count": aggregate.error_count,
            "error_rate": aggregate.error_rate,
            "recommendation": {},
            "breakdown": [],
            "fidelity": None,
            "no_valid_samples": True,
        }
        if fidelity is not None:
            out["fidelity"] = _fidelity_block(fidelity)
        _attach_causal_counterfactual(out, causal, counterfactual)
        _attach_m6_plus(out, rejection_analysis, trajectory, commentary)
        return out

    recommendation: dict[str, Any] = {}
    breakdown: list[dict[str, Any]] = []

    if aggregate.kind is DecisionKind.CHOOSE:
        share = aggregate.stats.get("share", {})
        recommendation["top"] = aggregate.stats.get("top")
        recommendation["share"] = share.get(recommendation["top"])
        # 按份额从大到小排序，作为前端易渲染的 list
        for opt, s in sorted(share.items(), key=lambda kv: kv[1], reverse=True):
            breakdown.append({"option": opt, "share": s,
                              "count": aggregate.stats["counts"].get(opt, 0)})
    else:
        # 数值 kind
        s = aggregate.stats
        recommendation["mean"] = s.get("mean")
        recommendation["confidence_band"] = (s.get("p25"), s.get("p75"))
        recommendation["range"] = (s.get("min"), s.get("max"))

    out = {
        "scenario": scenario_block,
        "persona_count": persona_count,
        "n_total": aggregate.n_total,
        "n_valid": aggregate.n_valid,
        "error_count": aggregate.error_count,
        "error_rate": aggregate.error_rate,
        "recommendation": recommendation,
        "breakdown": breakdown,
        "fidelity": None,
    }
    if fidelity is not None:
        out["fidelity"] = _fidelity_block(fidelity)
    _attach_causal_counterfactual(out, causal, counterfactual)
    _attach_m6_plus(out, rejection_analysis, trajectory, commentary)
    return out


def _normalize_trajectory(
    traj: list[Any] | None,
) -> list[dict[str, Any]] | None:
    if traj is None:
        return None
    out: list[dict[str, Any]] = []
    for p in traj:
        if isinstance(p, dict):
            out.append({
                "round_idx": p.get("round_idx"),
                "n_valid": p.get("n_valid"),
                "mean": p.get("mean"),
                "p25": p.get("p25"),
                "p75": p.get("p75"),
            })
        else:
            # dataclass-like (TrajectoryPoint)
            out.append({
                "round_idx": getattr(p, "round_idx", None),
                "n_valid": getattr(p, "n_valid", None),
                "mean": getattr(p, "mean", None),
                "p25": getattr(p, "p25", None),
                "p75": getattr(p, "p75", None),
            })
    return out


def _attach_m6_plus(
    out: dict[str, Any],
    rejection_analysis: dict[str, Any] | None,
    trajectory: list[Any] | None,
    commentary: str | None,
) -> None:
    """M6+ 三件套：rejection / trajectory / commentary。
    始终设置 key（None 表示未提供），让前端统一判断。
    """
    out["rejection_analysis"] = rejection_analysis if rejection_analysis else None
    out["trajectory"] = _normalize_trajectory(trajectory)
    out["commentary"] = commentary if commentary else None


def _attach_causal_counterfactual(out: dict[str, Any],
                                    causal: Any, counterfactual: Any) -> None:
    """把可选的 causal / counterfactual 报告挂到 out 里。
    始终设置 key（None 表示未提供），让前端可统一判断。
    """
    if causal is not None:
        out["causal"] = {
            "baseline_metric": causal.baseline_metric,
            "contributions": [
                {"factor_id": c.factor_id, "factor_label": c.factor_label,
                 "baseline_metric": c.baseline_metric,
                 "ablated_metric": c.ablated_metric,
                 "delta": c.delta, "abs_delta": c.abs_delta, "rank": c.rank}
                for c in causal.contributions],
            "notes": list(causal.notes),
        }
    else:
        out["causal"] = None
    if counterfactual is not None:
        out["counterfactual"] = {
            "baseline_label": counterfactual.baseline_label,
            "baseline_metric": counterfactual.baseline_metric,
            "outcomes": [
                {"alt_id": o.alt_id, "label": o.label, "metric": o.metric,
                 "delta_vs_baseline": o.delta_vs_baseline}
                for o in counterfactual.outcomes],
        }
    else:
        out["counterfactual"] = None


def render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    sc = report["scenario"]
    lines.append("# 万象模拟报告")
    lines.append("")
    lines.append(f"**研究目标**：{sc['question']}")
    lines.append(f"**投放材料**：{sc['material']}")
    lines.append(f"**虚拟人规模**：{report['persona_count']}")
    lines.append(
        f"**有效样本**：{report['n_valid']} / {report['n_total']}"
        f"（错误率 {report['error_rate']:.1%}，错误 {report['error_count']} 例）")
    lines.append("")

    # 退化分支：所有样本失效，不要尝试格式化 None
    if report.get("no_valid_samples"):
        lines.append("## ⚠️ 无有效样本")
        lines.append("")
        lines.append(
            "本次模拟未产生任何有效决策。可能原因：模型输出非合规 JSON、"
            "全部样本触发解析错误、或场景配置不当。请检查模型连接与场景设置。")
        lines.append("")
        lines.append("---")
        lines.append("*结果为概率预测，建议结合业务判断使用。*")
        return "\n".join(lines)

    lines.append("## 推荐结论")
    rec = report["recommendation"]
    if sc["decision_kind"] == "choose":
        lines.append(
            f"- 群体首选：**{rec['top']}**（份额 {rec['share']:.1%}）")
        lines.append("")
        lines.append("## 选项份额")
        for row in report["breakdown"]:
            lines.append(
                f"- {row['option']}: {row['share']:.1%}（{row['count']} 票）")
    else:
        mean = rec["mean"]
        band = rec["confidence_band"]
        rng = rec["range"]
        lines.append(f"- 群体均值：**{mean:.2f}**")
        lines.append(f"- 中段（p25–p75）：{band[0]} – {band[1]}")
        lines.append(f"- 整体范围：{rng[0]} – {rng[1]}")
    lines.append("")

    fid = report.get("fidelity")
    if fid is not None:
        lines.append("## 校准保真度")
        lines.append(
            f"- 总评：**{fid['label']}**（fidelity_score={fid['score']:.2f}）")
        lines.append(f"- Spearman: {fid['spearman']:.3f}")
        lines.append(f"- RMSE: {fid['rmse']:.3f}")
        lines.append(f"- 欧氏距离: {fid['euclidean']:.3f}")
        if fid["notes"]:
            lines.append("- 备注：")
            for n in fid["notes"]:
                lines.append(f"  - {n}")
        lines.append("")

    causal = report.get("causal")
    if causal:
        lines.append("## 因果归因")
        lines.append(f"基线指标：{causal['baseline_metric']:.2f}")
        lines.append("")
        if not causal["contributions"]:
            lines.append("（无有效因子）")
        else:
            lines.append("| 排名 | 因素 | 移除后 | Δ |")
            lines.append("|---|---|---|---|")
            for c in causal["contributions"]:
                lines.append(
                    f"| {c['rank']} | {c['factor_label']} | "
                    f"{c['ablated_metric']:.2f} | {c['delta']:+.2f} |")
        if causal.get("notes"):
            lines.append("")
            for n in causal["notes"]:
                lines.append(f"- _备注_: {n}")
        lines.append("")

    cf = report.get("counterfactual")
    if cf:
        lines.append("## 反事实推演")
        lines.append(
            f"基线（{cf['baseline_label']}）指标：{cf['baseline_metric']:.2f}")
        lines.append("")
        if not cf["outcomes"]:
            lines.append("（未提供替代方案）")
        else:
            lines.append("| 方案 | 指标 | Δ vs 基线 |")
            lines.append("|---|---|---|")
            for o in cf["outcomes"]:
                lines.append(
                    f"| {o['label']} | {o['metric']:.2f} | "
                    f"{o['delta_vs_baseline']:+.2f} |")
        lines.append("")

    # ---- M6+ 三件套 ----
    rej = report.get("rejection_analysis")
    if rej and rej.get("total_rejected", 0) > 0:
        lines.append("## 劝退原因构成")
        lines.append(
            f"被拒/低评样本共 **{rej['total_rejected']}** 例，按原因分布如下：")
        lines.append("")
        if rej.get("buckets"):
            lines.append("| 原因 | 占比 | 示例 |")
            lines.append("|---|---|---|")
            total = rej["total_rejected"] or 1
            for bucket, count in rej["buckets"].items():
                pct = count / total
                ex = (rej.get("examples", {}).get(bucket) or [""])[0]
                ex_short = ex[:30] + ("…" if len(ex) > 30 else "")
                lines.append(
                    f"| {bucket} | {count}（{pct:.1%}）| {ex_short} |")
        lines.append("")

    traj = report.get("trajectory")
    if traj and len(traj) >= 2:
        lines.append("## 群体情绪演化")
        lines.append("各轮次的群体均值/中段（p25–p75）：")
        lines.append("")
        lines.append("| round | n_valid | mean | p25 | p75 |")
        lines.append("|---|---|---|---|---|")
        for p in traj:
            mean = p.get("mean")
            p25 = p.get("p25")
            p75 = p.get("p75")
            mean_s = f"{mean:.2f}" if isinstance(mean, (int, float)) else "—"
            p25_s = f"{p25:.2f}" if isinstance(p25, (int, float)) else "—"
            p75_s = f"{p75:.2f}" if isinstance(p75, (int, float)) else "—"
            lines.append(
                f"| {p.get('round_idx')} | {p.get('n_valid')} | "
                f"{mean_s} | {p25_s} | {p75_s} |")
        lines.append("")

    commentary = report.get("commentary")
    if commentary:
        lines.append("## LLM 解读")
        lines.append(commentary)
        lines.append("")

    lines.append("---")
    lines.append("*结果为概率预测，建议结合业务判断使用。*")
    return "\n".join(lines)
