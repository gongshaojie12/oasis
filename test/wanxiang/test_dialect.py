# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import os

import pytest

from wanxiang.actions.dialect import DialectLoader, PlatformDialect

DIALECT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "..", "wanxiang", "actions", "l3_dialects",
)


@pytest.fixture
def loader():
    return DialectLoader(DIALECT_DIR)


def test_load_xiaohongshu_basic_fields(loader):
    d = loader.load("xiaohongshu")
    assert isinstance(d, PlatformDialect)
    assert d.name == "xiaohongshu"
    assert d.display_name == "小红书"
    assert d.relationship == "weak"
    assert d.feed_algorithm == "recommend"


def test_alias_resolution(loader):
    d = loader.load("xiaohongshu")
    assert d.alias_of("publish") == "发笔记"
    assert d.alias_of("collect") == "收藏"


def test_disabled_action_not_supported(loader):
    d = loader.load("xiaohongshu")
    assert d.supports("dislike") is False
    assert d.supports("like") is True


def test_unsupported_action_alias_raises(loader):
    d = loader.load("xiaohongshu")
    with pytest.raises(KeyError):
        d.alias_of("dislike")


def test_extra_metadata_preserved(loader):
    d = loader.load("xiaohongshu")
    assert d.extra_of("collect") == {"合集": True}
    assert d.extra_of("publish") == {}


def test_supported_action_names(loader):
    d = loader.load("xiaohongshu")
    names = d.supported_action_names()
    assert "publish" in names
    assert "dislike" not in names


def test_unknown_action_in_yaml_rejected(loader, tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "name: bad\ndisplay_name: Bad\nrelationship: none\n"
        "feed_algorithm: hotscore\n"
        "supported_actions:\n  nonexistent_action: {alias: x}\n",
        encoding="utf-8",
    )
    bad_loader = DialectLoader(str(tmp_path))
    with pytest.raises(ValueError, match="not a known L2 action"):
        bad_loader.load("bad")


def test_load_missing_dialect_raises(loader):
    with pytest.raises(FileNotFoundError):
        loader.load("nonexistent_platform")
