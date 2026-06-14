# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""媒体环境注入 (M4 MVP)。

让每个 persona 在做 L1 决策前"看到"一段动态推荐信息流：从 media_pool
中按 persona 兴趣关键词 + 渠道偏好排序，取 top-K，作为 system prompt
的前置上下文。

MVP 采用关键词重叠 + 渠道偏好的简单排序器；spec §M4 提到的完整 OASIS
recsys 集成留作后续迭代（保持 Ranker 接口稳定即可无缝替换）。

排序公式（KeywordRanker）：
    score = 2 * |item.tags ∩ persona_keywords|
          + 1 * |title.split() ∩ persona_keywords|
          + 3 * (item.channel in persona_preferred_channels)
    稳定排序：相同 score 保持原顺序。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence


@dataclass(frozen=True)
class MediaItem:
    """单条内容池条目。frozen 以便复用 / hash。

    - item_id: 唯一标识（业务侧自定义）
    - title:   标题
    - body:    正文（可空）
    - channel: 来源渠道，建议与 persona.media 键对齐（如 "xhs", "douyin"）
    - tags:    标签 tuple（语义关键词）
    - author:  作者（可空，预留）
    """

    item_id: str
    title: str
    body: str = ""
    channel: str = ""
    tags: tuple[str, ...] = ()
    author: str | None = None


class Ranker(Protocol):
    """Persona-aware 排序器协议。Stateless；纯函数语义。

    实现方按 persona 画像对 pool 排序，返回 top-K（顺序敏感）。
    未来接入 OASIS recsys / TwHIN / 向量召回时实现该协议即可。
    """

    def rank(self, persona, pool: Sequence[MediaItem],
             k: int) -> list[MediaItem]:
        ...


def _extract_keywords(persona) -> set[str]:
    """从 persona.personality + persona.demographic 抽取关键词集合。

    兼容：
    - dict 值是 str → split() 后并入
    - dict 值是 list/tuple/set → 每个 str 元素 split() 后并入
    - 其它类型 → 跳过
    """
    out: set[str] = set()
    for group in (getattr(persona, "personality", None),
                  getattr(persona, "demographic", None)):
        if not isinstance(group, dict):
            continue
        for v in group.values():
            if isinstance(v, str):
                out.update(v.split())
            elif isinstance(v, (list, tuple, set)):
                for x in v:
                    if isinstance(x, str):
                        out.update(x.split())
    return out


def _extract_preferred_channels(persona) -> set[str]:
    """从 persona.media 抽取偏好渠道。

    persona.media 是 dict[str, float]（spec §M2：键=渠道名，值=权重 0-1）。
    任何在 media 中"被提及"的渠道都视为偏好（MVP 不区分权重阈值）。
    """
    media = getattr(persona, "media", None)
    if isinstance(media, dict) and media:
        return {k for k in media.keys() if isinstance(k, str)}
    return set()


class KeywordRanker:
    """MVP 排序器：persona 兴趣关键词 ∩ item 标签/标题 + 偏好渠道加成。

    详见模块 docstring 中的排序公式。空池 / k<=0 → []。
    """

    def rank(self, persona, pool: Sequence[MediaItem],
             k: int) -> list[MediaItem]:
        if not pool or k <= 0:
            return []
        keywords = _extract_keywords(persona)
        pref_channels = _extract_preferred_channels(persona)

        # (-score, original_index, item) → 稳定降序
        scored: list[tuple[int, int, MediaItem]] = []
        for idx, item in enumerate(pool):
            score = 0
            if keywords:
                score += 2 * len(set(item.tags) & keywords)
                score += len(set(item.title.split()) & keywords)
            if item.channel and item.channel in pref_channels:
                score += 3
            scored.append((-score, idx, item))
        scored.sort()
        return [t[2] for t in scored[:k]]


def select_feed(persona, pool: Sequence[MediaItem], k: int,
                ranker: Ranker | None = None) -> list[MediaItem]:
    """高层 helper：选 top-K 条推荐内容。

    供模拟流水线调用。默认用 KeywordRanker，可注入自定义 Ranker。
    """
    if not pool or k <= 0:
        return []
    return (ranker or KeywordRanker()).rank(persona, pool, k)


def render_feed_prompt(feed: Sequence[MediaItem]) -> str:
    """把已选 feed 渲染为 system prompt 前缀文本。

    空 feed → 空字符串（调用方据此跳过注入，保证向后兼容）。
    """
    if not feed:
        return ""
    lines: list[str] = ["【你最近在信息流看到的内容】"]
    for i, item in enumerate(feed, 1):
        channel_part = f"[{item.channel}] " if item.channel else ""
        lines.append(f"{i}. {channel_part}{item.title}")
        if item.body:
            lines.append(f"   {item.body}")
    lines.append("")  # 与下文之间留空行
    return "\n".join(lines)
