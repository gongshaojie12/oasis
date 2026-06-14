# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""KeywordRanker + select_feed + render_feed_prompt (M4 MVP)."""
from __future__ import annotations

import pytest

from wanxiang.media.environment import (KeywordRanker, MediaItem,
                                         render_feed_prompt, select_feed)
from wanxiang.personas.persona import Persona


def _persona(media=None, personality=None, demographic=None):
    return Persona(
        agent_id=0, name="测试者",
        demographic=demographic or {"年龄": 25, "城市": "上海"},
        personality=personality or {"interests": ["coffee", "fashion", "running"]},
        media=media if media is not None else {"xhs": 0.8, "douyin": 0.6},
    )


def _item(item_id, title="", body="", channel="xhs", tags=()):
    return MediaItem(item_id=item_id, title=title, body=body,
                     channel=channel, tags=tuple(tags))


def test_empty_pool_returns_empty():
    assert select_feed(_persona(), [], 5) == []


def test_k_zero_returns_empty():
    assert select_feed(_persona(), [_item("a")], 0) == []


def test_negative_k_returns_empty():
    assert select_feed(_persona(), [_item("a"), _item("b")], -1) == []


def test_k_larger_than_pool_returns_all():
    pool = [_item("a"), _item("b")]
    out = select_feed(_persona(), pool, 10)
    assert len(out) == 2


def test_tag_overlap_ranks_higher():
    pool = [_item("a", tags=("coffee", "running")),
            _item("b", tags=("politics",))]
    out = select_feed(_persona(), pool, 2)
    assert out[0].item_id == "a"
    assert out[1].item_id == "b"


def test_channel_preference_breaks_ties():
    # both have no tag overlap; xhs persona prefers xhs
    pool = [_item("a", channel="weibo"),  # not preferred
            _item("b", channel="xhs")]    # preferred
    out = select_feed(_persona(), pool, 2)
    assert out[0].item_id == "b"


def test_render_feed_empty():
    assert render_feed_prompt([]) == ""


def test_render_feed_includes_channel_and_title():
    feed = [_item("a", title="精选好物", channel="xhs"),
            _item("b", title="爆款", channel="douyin")]
    out = render_feed_prompt(feed)
    assert "精选好物" in out
    assert "爆款" in out
    assert "xhs" in out
    assert "douyin" in out
    assert "信息流" in out


def test_render_feed_includes_body_if_present():
    feed = [_item("a", title="t", body="详细描述")]
    out = render_feed_prompt(feed)
    assert "详细描述" in out


def test_keyword_ranker_stable_for_zero_scores():
    """All items tie at 0 → original order preserved."""
    # persona has no channel/tag overlap with these items
    p = _persona(media={}, personality={})
    pool = [_item(f"x{i}", channel="weibo") for i in range(5)]
    out = select_feed(p, pool, 5)
    ids = [it.item_id for it in out]
    assert ids == ["x0", "x1", "x2", "x3", "x4"]


def test_persona_without_interests_doesnt_crash():
    p = Persona(agent_id=1, name="x",
                demographic={}, personality={}, media={})
    pool = [_item("a", channel="xhs", tags=("coffee",))]
    out = select_feed(p, pool, 1)
    assert len(out) == 1


def test_keyword_ranker_direct_interface():
    """Ranker class can be used directly (Protocol compliance)."""
    r = KeywordRanker()
    p = _persona()
    pool = [_item("a", tags=("coffee",)), _item("b", tags=("nothing",))]
    out = r.rank(p, pool, 2)
    assert out[0].item_id == "a"


def test_chinese_keyword_overlap_via_split():
    """tags / title 中文关键词 via persona personality strings."""
    p = _persona(personality={"hobby": ["精选 咖啡"]},
                 media={"xhs": 0.7})
    pool = [_item("a", title="精选", channel="xhs"),
            _item("b", title="无关", channel="xhs")]
    out = select_feed(p, pool, 2)
    assert out[0].item_id == "a"
