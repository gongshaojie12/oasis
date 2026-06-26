# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""把 AggregateReport (+ 可选 FidelityReport) 渲染为结构化 dict 与
人类可读 Markdown。dict 给 chat.html 工件卡用；Markdown 给 PDF/邮件
导出。

P3: 支持 locale="zh"/"en" 双语渲染。默认 zh，旧 caller 零回归。
"""
from __future__ import annotations

from typing import Any

from wanxiang.calibration.fidelity import FidelityReport
from wanxiang.reporting.i18n import DEFAULT_LOCALE, fidelity_label, label
from wanxiang.simulation.aggregate import AggregateReport
from wanxiang.simulation.scenario import DecisionKind, ScenarioConfig


def _fidelity_label(score: float) -> str:
    # backwards-compatible (Chinese, no-locale) helper retained for callers
    # that still import it directly (none in tree as of P3, but keep stable).
    return fidelity_label(score, locale="zh")


def _fidelity_block(fidelity: FidelityReport, locale: str = "zh") -> dict[str, Any]:
    return {
        "score": fidelity.fidelity_score,
        "label": fidelity_label(fidelity.fidelity_score, locale=locale),
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
    locale: str = DEFAULT_LOCALE,
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
            "locale": locale,
        }
        if fidelity is not None:
            out["fidelity"] = _fidelity_block(fidelity, locale=locale)
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
        recommendation["median"] = s.get("median")
        recommendation["confidence_band"] = (s.get("p25"), s.get("p75"))
        recommendation["range"] = (s.get("min"), s.get("max"))
        recommendation["histogram"] = s.get("histogram")

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
        "locale": locale,
    }
    if fidelity is not None:
        out["fidelity"] = _fidelity_block(fidelity, locale=locale)
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


def render_markdown(report: dict[str, Any], *,
                     locale: str | None = None) -> str:
    """Render the report dict to Markdown.

    Locale resolution: explicit ``locale`` arg > ``report['locale']`` > zh.
    """
    loc = locale or report.get("locale") or DEFAULT_LOCALE

    def L(key: str, **kw) -> str:
        return label(key, locale=loc, **kw)

    lines: list[str] = []
    sc = report["scenario"]
    colon = L("punct.colon")
    lines.append(f"# {L('title.main')}")
    lines.append("")
    lines.append(f"**{L('field.question')}**{colon}{sc['question']}")
    lines.append(f"**{L('field.material')}**{colon}{sc['material']}")
    lines.append(
        f"**{L('field.persona_count')}**{colon}{report['persona_count']}")
    err_rate_str = f"{report['error_rate']:.1%}"
    lines.append(
        f"**{L('field.valid_samples')}**{colon}"
        + L("field.valid_samples_template",
            n_valid=report['n_valid'], n_total=report['n_total'],
            error_rate=err_rate_str, error_count=report['error_count']))
    lines.append("")

    # 退化分支：所有样本失效，不要尝试格式化 None
    if report.get("no_valid_samples"):
        lines.append(f"## {L('section.no_valid_samples_heading')}")
        lines.append("")
        lines.append(L("no_valid_samples.body"))
        lines.append("")
        lines.append("---")
        lines.append(L("disclaimer"))
        return "\n".join(lines)

    lines.append(f"## {L('section.recommendation')}")
    rec = report["recommendation"]
    if sc["decision_kind"] == "choose":
        share_str = f"{rec['share']:.1%}"
        lines.append(
            "- " + L("reco.top_choice_template",
                     top=rec['top'], share=share_str))
        lines.append("")
        lines.append(f"## {L('section.option_share')}")
        for row in report["breakdown"]:
            row_share = f"{row['share']:.1%}"
            lines.append(
                "- " + L("reco.option_row_template",
                         option=row['option'], share=row_share,
                         count=row['count']))
    else:
        mean = rec["mean"]
        band = rec["confidence_band"]
        rng = rec["range"]
        mean_s = f"{mean:.2f}"
        lines.append("- " + L("reco.mean_template", mean=mean_s))
        lines.append("- " + L("reco.confidence_band_template",
                              lo=band[0], hi=band[1]))
        lines.append("- " + L("reco.range_template",
                              lo=rng[0], hi=rng[1]))
    lines.append("")

    fid = report.get("fidelity")
    if fid is not None:
        lines.append(f"## {L('section.fidelity')}")
        score_s = f"{fid['score']:.2f}"
        spearman_s = f"{fid['spearman']:.3f}"
        rmse_s = f"{fid['rmse']:.3f}"
        eucl_s = f"{fid['euclidean']:.3f}"
        lines.append("- " + L("fidelity.overall_template",
                              label=fid['label'], score=score_s))
        lines.append("- " + L("fidelity.spearman_template", value=spearman_s))
        lines.append("- " + L("fidelity.rmse_template", value=rmse_s))
        lines.append("- " + L("fidelity.euclidean_template", value=eucl_s))
        if fid["notes"]:
            lines.append("- " + L("fidelity.notes_label"))
            for n in fid["notes"]:
                lines.append(f"  - {n}")
        lines.append("")

    causal = report.get("causal")
    if causal:
        lines.append(f"## {L('section.factor_contributions')}")
        baseline_s = f"{causal['baseline_metric']:.2f}"
        lines.append(L("causal.baseline_metric_template", value=baseline_s))
        lines.append("")
        if not causal["contributions"]:
            lines.append(L("causal.no_factors"))
        else:
            lines.append(
                f"| {L('header.rank')} | {L('header.factor')} | "
                f"{L('header.ablated')} | {L('header.delta')} |")
            lines.append("|---|---|---|---|")
            for c in causal["contributions"]:
                lines.append(
                    f"| {c['rank']} | {c['factor_label']} | "
                    f"{c['ablated_metric']:.2f} | {c['delta']:+.2f} |")
        if causal.get("notes"):
            lines.append("")
            for n in causal["notes"]:
                lines.append("- " + L("causal.note_template", note=n))
        lines.append("")

    cf = report.get("counterfactual")
    if cf:
        lines.append(f"## {L('section.counterfactuals')}")
        baseline_s = f"{cf['baseline_metric']:.2f}"
        lines.append(L("cf.baseline_template",
                       label=cf['baseline_label'], value=baseline_s))
        lines.append("")
        if not cf["outcomes"]:
            lines.append(L("cf.no_alternatives"))
        else:
            lines.append(
                f"| {L('header.scheme')} | {L('header.metric_value')} | "
                f"{L('header.delta_vs_baseline')} |")
            lines.append("|---|---|---|")
            for o in cf["outcomes"]:
                lines.append(
                    f"| {o['label']} | {o['metric']:.2f} | "
                    f"{o['delta_vs_baseline']:+.2f} |")
        lines.append("")

    # ---- M6+ 三件套 ----
    rej = report.get("rejection_analysis")
    if rej and rej.get("total_rejected", 0) > 0:
        lines.append(f"## {L('section.rejection')}")
        lines.append(L("rejection.summary_template", n=rej['total_rejected']))
        lines.append("")
        if rej.get("buckets"):
            lines.append(
                f"| {L('header.reason')} | {L('header.percent')} | "
                f"{L('header.examples')} |")
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
        lines.append(f"## {L('section.trajectory')}")
        lines.append(L("trajectory.intro"))
        lines.append("")
        lines.append(
            f"| {L('header.round')} | {L('header.n_valid')} | "
            f"{L('header.mean')} | {L('header.p25')} | {L('header.p75')} |")
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
        lines.append(f"## {L('section.llm_commentary')}")
        lines.append(commentary)
        lines.append("")

    lines.append("---")
    lines.append(L("disclaimer"))
    return "\n".join(lines)
