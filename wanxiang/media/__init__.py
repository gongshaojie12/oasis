# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""媒体环境注入 (spec §M4 MVP)。

公开接口：
- MediaItem: 内容池条目（冻结 dataclass）
- Ranker: 排序器协议（rank(persona, pool, k) -> list[MediaItem]）
- KeywordRanker: MVP 排序器（关键词重叠 + 渠道偏好）
- select_feed: 高层 helper
- render_feed_prompt: 把选中条目渲染为 system prompt 前缀
"""
from wanxiang.media.environment import (KeywordRanker, MediaItem, Ranker,
                                         render_feed_prompt, select_feed)

__all__ = [
    "MediaItem",
    "Ranker",
    "KeywordRanker",
    "select_feed",
    "render_feed_prompt",
]
