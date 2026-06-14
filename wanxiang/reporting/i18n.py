# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""Report-layer i18n labels (P3).

Separate from ``wanxiang.api.i18n`` because the report catalog is much
larger (headings + table headers + units + disclaimers) and has a
different review/translation flow than the API error catalog.

Locale resolution: explicit parameter wins; missing keys return the key
verbatim (visible in tests); missing translation falls back to ``zh``.
"""
from __future__ import annotations

from typing import Literal

Locale = Literal["zh", "en"]
DEFAULT_LOCALE: Locale = "zh"

# Catalog keyed by namespace.key → {zh, en}
LABELS: dict[str, dict[str, str]] = {
    # ---- title ----
    "title.main": {
        "zh": "万象模拟报告",
        "en": "WANXIANG Simulation Report",
    },
    "title.subtitle_template": {
        "zh": "决策类型: {kind} · 样本: {n_valid}/{n_total}",
        "en": "Decision kind: {kind} · Sample: {n_valid}/{n_total}",
    },
    # ---- header field labels (used inline at top of markdown) ----
    "field.question": {"zh": "研究目标", "en": "Research goal"},
    "field.material": {"zh": "投放材料", "en": "Material"},
    "field.persona_count": {"zh": "虚拟人规模", "en": "Persona count"},
    "field.valid_samples": {"zh": "有效样本", "en": "Valid samples"},
    "field.valid_samples_template": {
        "zh": "{n_valid} / {n_total}（错误率 {error_rate}，错误 {error_count} 例）",
        "en": "{n_valid} / {n_total} (error rate {error_rate}, {error_count} errors)",
    },
    # Punctuation: full-width colon for zh, ASCII colon+space for en
    "punct.colon": {"zh": "：", "en": ": "},
    # ---- sections ----
    "section.executive_summary": {
        "zh": "执行摘要", "en": "Executive Summary",
    },
    "section.aggregate": {
        "zh": "聚合结果", "en": "Aggregate Results",
    },
    "section.recommendation": {
        "zh": "推荐结论", "en": "Recommendation",
    },
    "section.option_share": {
        "zh": "选项份额", "en": "Option Share",
    },
    "section.fidelity": {
        "zh": "校准保真度", "en": "Calibration Fidelity",
    },
    "section.factor_contributions": {
        "zh": "因果归因", "en": "Causal Attribution",
    },
    "section.counterfactuals": {
        "zh": "反事实推演", "en": "Counterfactual Reasoning",
    },
    "section.rejection": {
        "zh": "劝退原因构成", "en": "Rejection Reasons Breakdown",
    },
    "section.trajectory": {
        "zh": "群体情绪演化", "en": "Sentiment Trajectory",
    },
    "section.llm_commentary": {
        "zh": "LLM 解读", "en": "LLM Commentary",
    },
    "section.scenario": {"zh": "场景信息", "en": "Scenario"},
    "section.no_valid_samples_heading": {
        "zh": "⚠️ 无有效样本",
        "en": "⚠️ No Valid Samples",
    },
    # ---- recommendation (choose) ----
    "reco.top_choice_template": {
        "zh": "群体首选：**{top}**（份额 {share}）",
        "en": "Top choice: **{top}** (share {share})",
    },
    "reco.option_row_template": {
        "zh": "{option}: {share}（{count} 票）",
        "en": "{option}: {share} ({count} votes)",
    },
    # ---- recommendation (numeric) ----
    "reco.mean_template": {
        "zh": "群体均值：**{mean}**",
        "en": "Population mean: **{mean}**",
    },
    "reco.confidence_band_template": {
        "zh": "中段（p25–p75）：{lo} – {hi}",
        "en": "Confidence band (p25–p75): {lo} – {hi}",
    },
    "reco.range_template": {
        "zh": "整体范围：{lo} – {hi}",
        "en": "Range: {lo} – {hi}",
    },
    # ---- fidelity ----
    "fidelity.overall_template": {
        "zh": "总评：**{label}**（fidelity_score={score}）",
        "en": "Overall: **{label}** (fidelity_score={score})",
    },
    "fidelity.spearman_template": {
        "zh": "Spearman: {value}",
        "en": "Spearman: {value}",
    },
    "fidelity.rmse_template": {
        "zh": "RMSE: {value}",
        "en": "RMSE: {value}",
    },
    "fidelity.euclidean_template": {
        "zh": "欧氏距离: {value}",
        "en": "Euclidean distance: {value}",
    },
    "fidelity.notes_label": {"zh": "备注：", "en": "Notes:"},
    "fidelity.label_high": {"zh": "高", "en": "High"},
    "fidelity.label_mid": {"zh": "中", "en": "Medium"},
    "fidelity.label_low": {"zh": "低", "en": "Low"},
    # ---- causal ----
    "causal.baseline_metric_template": {
        "zh": "基线指标：{value}",
        "en": "Baseline metric: {value}",
    },
    "causal.no_factors": {
        "zh": "（无有效因子）",
        "en": "(no valid factors)",
    },
    "causal.note_template": {
        "zh": "_备注_: {note}",
        "en": "_Note_: {note}",
    },
    # ---- counterfactual ----
    "cf.baseline_template": {
        "zh": "基线（{label}）指标：{value}",
        "en": "Baseline ({label}) metric: {value}",
    },
    "cf.no_alternatives": {
        "zh": "（未提供替代方案）",
        "en": "(no alternatives provided)",
    },
    # ---- rejection ----
    "rejection.summary_template": {
        "zh": "被拒/低评样本共 **{n}** 例，按原因分布如下：",
        "en": "**{n}** rejected/low-rated samples; distribution by reason:",
    },
    # ---- trajectory ----
    "trajectory.intro": {
        "zh": "各轮次的群体均值/中段（p25–p75）：",
        "en": "Per-round population mean and confidence band (p25–p75):",
    },
    # ---- table headers ----
    "header.metric": {"zh": "指标", "en": "Metric"},
    "header.value": {"zh": "数值", "en": "Value"},
    "header.factor": {"zh": "因子", "en": "Factor"},
    "header.baseline": {"zh": "基线值", "en": "Baseline"},
    "header.alternative": {"zh": "替代值", "en": "Alternative"},
    "header.delta": {"zh": "Δ", "en": "Δ"},
    "header.option": {"zh": "选项", "en": "Option"},
    "header.share": {"zh": "份额", "en": "Share"},
    "header.count": {"zh": "次数", "en": "Count"},
    "header.percent": {"zh": "占比", "en": "Percent"},
    "header.rank": {"zh": "排名", "en": "Rank"},
    "header.ablated": {"zh": "移除后", "en": "After ablation"},
    "header.scheme": {"zh": "方案", "en": "Scheme"},
    "header.metric_value": {"zh": "指标", "en": "Metric"},
    "header.delta_vs_baseline": {"zh": "Δ vs 基线", "en": "Δ vs baseline"},
    "header.reason": {"zh": "原因", "en": "Reason"},
    "header.examples": {"zh": "示例", "en": "Example"},
    "header.bucket": {"zh": "原因桶", "en": "Reason bucket"},
    "header.round": {"zh": "round", "en": "round"},
    "header.n_valid": {"zh": "n_valid", "en": "n_valid"},
    "header.mean": {"zh": "mean", "en": "mean"},
    "header.p25": {"zh": "p25", "en": "p25"},
    "header.p75": {"zh": "p75", "en": "p75"},
    # ---- disclaimer ----
    "disclaimer": {
        "zh": "*结果为概率预测，建议结合业务判断使用。*",
        "en": "*Results are probabilistic forecasts; combine with business judgment.*",
    },
    # ---- no-valid-samples branch body ----
    "no_valid_samples.body": {
        "zh": "本次模拟未产生任何有效决策。可能原因：模型输出非合规 JSON、"
              "全部样本触发解析错误、或场景配置不当。请检查模型连接与场景设置。",
        "en": "No valid decisions produced. Possible causes: malformed JSON "
              "from the model, all samples raised parse errors, or scenario "
              "misconfiguration. Check the model connection and scenario.",
    },
    # ---- decision kind display labels ----
    "kind.rate": {
        "zh": "评分 (0-10)", "en": "Rate (0-10)",
    },
    "kind.choose": {"zh": "多选一", "en": "Choose"},
    "kind.sentiment": {
        "zh": "情感极性 (-1 ~ +1)", "en": "Sentiment (-1 to +1)",
    },
    "kind.click_probability": {
        "zh": "点击概率 (0-1)", "en": "Click probability (0-1)",
    },
    "kind.willingness_to_pay": {
        "zh": "愿付价格", "en": "Willingness to pay",
    },
    "kind.purchase_intent": {
        "zh": "购买意愿", "en": "Purchase intent",
    },
    # ---- scenario field labels ----
    "scenario.kind": {"zh": "决策类型", "en": "Decision Kind"},
    "scenario.material": {"zh": "投放材料", "en": "Material"},
    "scenario.question": {"zh": "提问", "en": "Question"},
    "scenario.platform": {"zh": "平台", "en": "Platform"},
}


def label(key: str, *, locale: str = DEFAULT_LOCALE, **kwargs) -> str:
    """Look up ``key`` in the catalog.

    Missing key → return the key verbatim. Missing translation for the
    requested locale → fall back to zh. If ``kwargs`` are provided, format
    the template; any KeyError swallows back to the raw template (so
    a partially-supplied call still returns something useful).
    """
    entry = LABELS.get(key)
    if entry is None:
        return key
    template = entry.get(locale) or entry.get(DEFAULT_LOCALE) or key
    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError):
            return template
    return template


def kind_label(kind: str, *, locale: str = DEFAULT_LOCALE) -> str:
    """Map a DecisionKind enum value (or its .value string) to a human label.

    Unknown kinds pass through unchanged (so callers can pass arbitrary
    strings without exploding).
    """
    key = f"kind.{kind}"
    if key in LABELS:
        return label(key, locale=locale)
    return kind


def fidelity_label(score: float, *, locale: str = DEFAULT_LOCALE) -> str:
    """Bucket a fidelity score into a human label (High / Medium / Low)."""
    if score >= 0.85:
        return label("fidelity.label_high", locale=locale)
    if score >= 0.6:
        return label("fidelity.label_mid", locale=locale)
    return label("fidelity.label_low", locale=locale)


__all__ = [
    "LABELS", "label", "kind_label", "fidelity_label",
    "Locale", "DEFAULT_LOCALE",
]
