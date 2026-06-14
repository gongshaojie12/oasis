# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""P4: render_feed_prompt(locale=) bilingual heading."""
from __future__ import annotations

from wanxiang.media.environment import MediaItem, render_feed_prompt


def _feed():
    return [
        MediaItem(item_id="a", title="t1", body="b1", channel="xhs",
                  tags=("x",)),
        MediaItem(item_id="b", title="t2", body="", channel="douyin",
                  tags=("y",)),
    ]


def test_default_locale_renders_chinese_heading():
    out = render_feed_prompt(_feed())
    assert "【你最近在信息流看到的内容】" in out
    assert "t1" in out


def test_en_locale_renders_english_heading():
    out = render_feed_prompt(_feed(), locale="en")
    assert "feed" in out.lower()
    assert "[" in out and "]" in out  # english bracket style
    assert "t1" in out
    # zh heading absent
    assert "【你最近在信息流看到的内容】" not in out


def test_empty_feed_returns_empty_string_regardless_of_locale():
    assert render_feed_prompt([]) == ""
    assert render_feed_prompt([], locale="en") == ""
    assert render_feed_prompt([], locale="zh") == ""
