# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""Moderation interfaces."""
import asyncio
import pytest

from wanxiang.compliance.moderation import (
    NoOpModerator, KeywordBlocklistModerator, ModerationVerdict)


def test_noop_returns_safe():
    r = asyncio.run(NoOpModerator().check("任何内容"))
    assert r.verdict == ModerationVerdict.SAFE


def test_noop_returns_safe_for_offensive():
    r = asyncio.run(NoOpModerator().check("violence kill hate"))
    assert r.verdict == ModerationVerdict.SAFE


def test_blocklist_flags_match():
    m = KeywordBlocklistModerator(["badword", "禁词"])
    r = asyncio.run(m.check("This contains BadWord"))
    assert r.verdict == ModerationVerdict.UNSAFE
    assert "badword" in r.categories


def test_blocklist_passes_clean_text():
    m = KeywordBlocklistModerator(["badword"])
    r = asyncio.run(m.check("clean content"))
    assert r.verdict == ModerationVerdict.SAFE


def test_blocklist_case_insensitive():
    m = KeywordBlocklistModerator(["FoO"])
    r = asyncio.run(m.check("this has foo"))
    assert r.verdict == ModerationVerdict.UNSAFE
