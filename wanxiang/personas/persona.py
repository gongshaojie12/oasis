# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""Persona: 一个虚拟人的完整画像（冻结、可值比较）。

spec §M2 三组特质：
- demographic: 人口标签（年龄/性别/城市/收入/职业/教育 …）
- personality: 个性向量（价格敏感度/尝鲜意愿/健康意识/从众倾向 …）
- media:       媒体消费习惯（小红书/抖音/微信/B站/微博 … 权重 0-1）

每个 group 是 dict[str, Any]，键名由调用方决定（spec 目标 220+ 维，
本数据层不约束维度数，只提供容器与一致的 system prompt 渲染）。

P4 i18n: render_system_prompt(locale="zh"|"en")
- 默认 zh，向后兼容所有现有调用。
- en: 章节小标题英文化，trait key 通过 _PERSONA_LABEL_I18N 字典翻译；
  未命中字典的 key 保留原文（P5 会用 locale-aware yaml 解决根源）。
- value 本轮不翻译（来自 yaml 分布，P5 改造）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# P4: 已知 trait key 的双语字典。未命中的 key 渲染时保留原 zh 字面值。
_PERSONA_LABEL_I18N: dict[str, dict[str, str]] = {
    # demographic - core
    "城市": {"zh": "城市", "en": "city"},
    "性别": {"zh": "性别", "en": "gender"},
    "年龄": {"zh": "年龄", "en": "age"},
    "年龄段": {"zh": "年龄段", "en": "age band"},
    "省份": {"zh": "省份", "en": "province"},
    "月收入区间": {"zh": "月收入区间", "en": "monthly income range"},
    "月收入": {"zh": "月收入", "en": "monthly income"},
    "城市层级": {"zh": "城市层级", "en": "city tier"},
    "学历": {"zh": "学历", "en": "education"},
    "职业类型": {"zh": "职业类型", "en": "occupation type"},
    "职业": {"zh": "职业", "en": "occupation"},
    "婚姻状态": {"zh": "婚姻状态", "en": "marital status"},
    "家庭规模": {"zh": "家庭规模", "en": "household size"},
    "是否有子女": {"zh": "是否有子女", "en": "has children"},
    "子女数量": {"zh": "子女数量", "en": "children count"},
    "居住状态": {"zh": "居住状态", "en": "living arrangement"},
    "民族": {"zh": "民族", "en": "ethnicity"},
    "国籍": {"zh": "国籍", "en": "nationality"},
    # personality - common
    "价格敏感度": {"zh": "价格敏感度", "en": "price sensitivity"},
    "尝鲜意愿": {"zh": "尝鲜意愿", "en": "novelty seeking"},
    "健康意识": {"zh": "健康意识", "en": "health consciousness"},
    "从众倾向": {"zh": "从众倾向", "en": "conformity"},
    "外向性": {"zh": "外向性", "en": "extraversion"},
    "宜人性": {"zh": "宜人性", "en": "agreeableness"},
    "尽责性": {"zh": "尽责性", "en": "conscientiousness"},
    "开放性": {"zh": "开放性", "en": "openness"},
    "神经质": {"zh": "神经质", "en": "neuroticism"},
    "品牌忠诚度": {"zh": "品牌忠诚度", "en": "brand loyalty"},
    "炫耀性消费": {"zh": "炫耀性消费", "en": "conspicuous consumption"},
    "理性消费": {"zh": "理性消费", "en": "rational consumption"},
    "实用主义": {"zh": "实用主义", "en": "pragmatism"},
    # media - channels often appear as keys
    "小红书": {"zh": "小红书", "en": "Xiaohongshu"},
    "抖音": {"zh": "抖音", "en": "Douyin"},
    "微信": {"zh": "微信", "en": "WeChat"},
    "B站": {"zh": "B站", "en": "Bilibili"},
    "微博": {"zh": "微博", "en": "Weibo"},
    "知乎": {"zh": "知乎", "en": "Zhihu"},
}


_SECTION_HEADINGS: dict[str, dict[str, str]] = {
    "demographic": {"zh": "【人口特征】", "en": "[Demographics]"},
    "demographic_empty": {
        "zh": "【人口特征】（未提供）",
        "en": "[Demographics] (not provided)",
    },
    "personality": {
        "zh": "【个性与决策倾向】（0-1 区间，越大越显著）",
        "en": "[Personality] (0-1 range, larger = stronger)",
    },
    "personality_empty": {
        "zh": "【个性与决策倾向】（未提供）",
        "en": "[Personality] (not provided)",
    },
    "media": {
        "zh": "【媒体消费习惯】（0-1 区间，越大越常用/越信任）",
        "en": "[Media Habits] (0-1 range, larger = more frequent/trusted)",
    },
    "media_empty": {
        "zh": "【媒体消费习惯】（未提供）",
        "en": "[Media Habits] (not provided)",
    },
}


_INTRO = {
    "zh": "你是「{name}」。",
    "en": "You are \"{name}\".",
}

_OUTRO = {
    "zh": ("请基于以上画像，在被问到任何决策、态度或选择时，按这个人的"
            "真实视角作答；不要解释你是 AI，不要复述画像。"),
    "en": ("Based on the profile above, when asked about any decision, "
            "attitude or choice, answer from this person's authentic "
            "perspective; do not explain that you are an AI, do not "
            "restate the profile."),
}


def _label(key: str, locale: str) -> str:
    """Look up a translated label for a trait key, falling back to the key itself."""
    entry = _PERSONA_LABEL_I18N.get(key)
    if entry is None:
        return key
    return entry.get(locale) or entry.get("zh") or key


def _section_heading(section: str, locale: str) -> str:
    entry = _SECTION_HEADINGS.get(section, {})
    return entry.get(locale) or entry.get("zh") or ""


def _kv_separator(locale: str) -> str:
    """zh uses full-width '：', en uses ': '."""
    return ": " if locale == "en" else "："


@dataclass(frozen=True)
class Persona:
    agent_id: int
    name: str
    demographic: dict[str, Any] = field(default_factory=dict)
    personality: dict[str, Any] = field(default_factory=dict)
    media: dict[str, Any] = field(default_factory=dict)
    # P5: 来源 locale（zh / en）；默认 zh 兼容历史调用。仅供
    # render_system_prompt 等下游自检使用，不参与 equality 比较时通常
    # 是相同 locale 才比较，无需在 __eq__ 上特殊处理。
    locale: str = "zh"
    # 联合分布(IPU/IPF)抽样时,同一户的成员共享 household_id;
    # 独立/边际抽样路径恒为 None(向后兼容,旧调用与等值不受影响)。
    household_id: int | None = None

    def trait_count(self) -> int:
        """三组特质合计维数（不含 name/agent_id）。"""
        return len(self.demographic) + len(self.personality) + len(self.media)

    def render_system_prompt(self, locale: str = "zh") -> str:
        """把画像渲染为 system prompt 文本，供 LLM 调用。

        locale="zh"（默认，向后兼容）→ 中文 prompt。
        locale="en" → 英文章节标题 + 翻译 trait label（value 不翻译）。
        未识别 locale 回退到 zh。
        """
        if locale not in ("zh", "en"):
            locale = "zh"
        sep = _kv_separator(locale)
        parts: list[str] = []
        parts.append(_INTRO[locale].format(name=self.name))

        # Demographic
        if self.demographic:
            parts.append(_section_heading("demographic", locale))
            for k, v in self.demographic.items():
                parts.append(f"- {_label(k, locale)}{sep}{v}")
        else:
            parts.append(_section_heading("demographic_empty", locale))

        # Personality
        if self.personality:
            parts.append(_section_heading("personality", locale))
            for k, v in self.personality.items():
                parts.append(f"- {_label(k, locale)}{sep}{v}")
        else:
            parts.append(_section_heading("personality_empty", locale))

        # Media
        if self.media:
            parts.append(_section_heading("media", locale))
            for k, v in self.media.items():
                parts.append(f"- {_label(k, locale)}{sep}{v}")
        else:
            parts.append(_section_heading("media_empty", locale))

        parts.append(_OUTRO[locale])
        return "\n".join(parts)
