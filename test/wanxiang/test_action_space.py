# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import os

import pytest

from wanxiang.actions.dialect import DialectLoader
from wanxiang.actions.layers import SimulationMode
from wanxiang.actions.space import resolve_action_space

DIALECT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "..", "wanxiang", "actions", "l3_dialects",
)


@pytest.fixture
def xhs():
    return DialectLoader(DIALECT_DIR).load("xiaohongshu")


def test_decision_only_returns_only_l1():
    space = resolve_action_space(SimulationMode.DECISION_ONLY)
    assert "rate" in space            # L1
    assert "publish" not in space     # 无 L2


def test_social_returns_l1_and_l2():
    space = resolve_action_space(SimulationMode.SOCIAL)
    assert "rate" in space            # L1
    assert "publish" in space         # L2 抽象名
    assert "dislike" in space         # L2 抽象名（未受平台限制）


def test_platform_filters_by_dialect(xhs):
    space = resolve_action_space(SimulationMode.PLATFORM, dialect=xhs)
    assert "rate" in space            # L1 始终在
    assert "publish" in space         # 小红书支持
    assert "dislike" not in space     # 小红书禁用了 dislike


def test_platform_without_dialect_raises():
    with pytest.raises(ValueError, match="requires a platform dialect"):
        resolve_action_space(SimulationMode.PLATFORM)


def test_non_platform_with_dialect_raises(xhs):
    with pytest.raises(ValueError, match="only PLATFORM mode accepts a dialect"):
        resolve_action_space(SimulationMode.SOCIAL, dialect=xhs)
