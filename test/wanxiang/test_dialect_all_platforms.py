# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import os

import pytest

from wanxiang.actions.dialect import DialectLoader

DIALECT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "..", "wanxiang", "actions", "l3_dialects",
)


@pytest.fixture
def loader():
    return DialectLoader(DIALECT_DIR)


@pytest.mark.parametrize("platform", ["twitter", "reddit", "douyin", "wechat"])
def test_all_dialects_load(loader, platform):
    d = loader.load(platform)
    assert d.name == platform


def test_reddit_has_dislike_downvote(loader):
    d = loader.load("reddit")
    assert d.supports("dislike") is True
    assert d.alias_of("dislike") == "downvote"
    assert d.relationship == "none"


def test_twitter_repost_and_weak_relationship(loader):
    d = loader.load("twitter")
    assert d.alias_of("repost") == "repost"
    assert d.relationship == "weak"


def test_wechat_is_strong_relationship(loader):
    d = loader.load("wechat")
    assert d.relationship == "strong"
    assert d.feed_algorithm == "following"


def test_douyin_recommend_feed(loader):
    d = loader.load("douyin")
    assert d.feed_algorithm == "recommend"
    assert d.alias_of("repost") == "分享"
