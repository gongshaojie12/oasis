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


def build_report(
    *,
    scenario: ScenarioConfig,
    aggregate: AggregateReport,
    persona_count: int,
    fidelity: FidelityReport | None = None,
) -> dict[str, Any]:
    if aggregate.n_total == 0:
        raise ValueError("cannot report on empty AggregateReport")

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

    out: dict[str, Any] = {
        "scenario": {
            "material": scenario.material,
            "question": scenario.question,
            "decision_kind": scenario.decision_kind.value,
            "options": list(scenario.options) if scenario.options else None,
        },
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
        out["fidelity"] = {
            "score": fidelity.fidelity_score,
            "label": _fidelity_label(fidelity.fidelity_score),
            "spearman": fidelity.spearman,
            "rmse": fidelity.rmse,
            "euclidean": fidelity.euclidean,
            "notes": list(fidelity.notes),
        }
    return out


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

    lines.append("---")
    lines.append("*结果为概率预测，建议结合业务判断使用。*")
    return "\n".join(lines)
