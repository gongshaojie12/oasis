# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""format_peer_signal(report, dialect=...) — phrasing varies by dialect."""
import os

import pytest

from wanxiang.actions.dialect import DialectLoader
from wanxiang.simulation.aggregate import AggregateReport
from wanxiang.simulation.scenario import DecisionKind
from wanxiang.simulation.social import format_peer_signal

DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "..", "wanxiang", "actions", "l3_dialects")


@pytest.fixture
def loader():
    return DialectLoader(DIR)


def _choose_rep():
    return AggregateReport(
        kind=DecisionKind.CHOOSE, n_total=10, n_valid=10,
        error_count=0, error_rate=0.0,
        stats={"counts": {"A": 6, "B": 3, "C": 1},
               "share": {"A": 0.6, "B": 0.3, "C": 0.1}, "top": "A"})


def _rate_rep():
    return AggregateReport(
        kind=DecisionKind.RATE, n_total=10, n_valid=10,
        error_count=0, error_rate=0.0,
        stats={"mean": 6.8, "median": 7, "p25": 5, "p75": 9,
               "min": 1, "max": 10})


# ---- 兼容旧调用 ----

def test_format_peer_signal_without_dialect_unchanged():
    sig = format_peer_signal(_choose_rep())
    # 保持旧文案
    assert "群体首选 A" in sig
    assert "60" in sig


# ---- 按 relationship 切换 ----

def test_wechat_uses_friends_phrasing(loader):
    d = loader.load("wechat")
    sig = format_peer_signal(_choose_rep(), dialect=d)
    assert "好友" in sig
    assert "A" in sig and "60" in sig


def test_reddit_uses_community_phrasing(loader):
    d = loader.load("reddit")
    sig = format_peer_signal(_choose_rep(), dialect=d)
    assert "社区" in sig
    assert "A" in sig


def test_douyin_uses_recommend_phrasing(loader):
    d = loader.load("douyin")
    sig = format_peer_signal(_choose_rep(), dialect=d)
    assert "推荐" in sig or "算法" in sig


def test_xiaohongshu_uses_recommend_phrasing(loader):
    d = loader.load("xiaohongshu")
    sig = format_peer_signal(_choose_rep(), dialect=d)
    assert "推荐" in sig or "算法" in sig


def test_twitter_uses_following_phrasing(loader):
    d = loader.load("twitter")
    sig = format_peer_signal(_choose_rep(), dialect=d)
    assert "关注" in sig


# ---- 数值 kind 也分平台 ----

def test_numeric_kind_with_wechat(loader):
    d = loader.load("wechat")
    sig = format_peer_signal(_rate_rep(), dialect=d)
    assert "好友" in sig
    assert "6.8" in sig


def test_numeric_kind_with_douyin(loader):
    d = loader.load("douyin")
    sig = format_peer_signal(_rate_rep(), dialect=d)
    assert "推荐" in sig or "算法" in sig
    assert "6.8" in sig


# ---- 空报告 ----

def test_empty_report_with_dialect_returns_neutral(loader):
    d = loader.load("wechat")
    rep = AggregateReport(kind=None, n_total=0, n_valid=0,
                          error_count=0, error_rate=0.0, stats={})
    sig = format_peer_signal(rep, dialect=d)
    assert isinstance(sig, str) and len(sig) > 0
