"""Tests for custom action type definitions."""

import pytest

from engine.platforms.actions import (
    ALL_CUSTOM_ACTIONS,
    COLLECT_POST,
    GIVE_COIN,
    PLATFORM_ACTIONS,
    POST_SHUOSHUO,
    SEND_DANMAKU,
    SEND_GIFT,
    SHARE_POST,
    SHARE_TO_FRIENDS,
    TRIPLE_TAP,
    get_platform_actions,
    is_custom_action,
)


class TestActionConstants:
    def test_all_constants_are_strings(self):
        for action in ALL_CUSTOM_ACTIONS:
            assert isinstance(action, str)
            assert len(action) > 0

    def test_no_overlap_with_core_actions(self):
        from oasis.social_platform.typing import ActionType

        core_values = {a.value for a in ActionType}
        overlap = ALL_CUSTOM_ACTIONS & core_values
        assert overlap == set(), (
            f"Custom actions overlap with core ActionType: {overlap}"
        )

    def test_platform_actions_mapping_complete(self):
        expected_platforms = {
            "weibo", "xiaohongshu", "douyin",
            "kuaishou", "bilibili", "wechat_video",
        }
        assert set(PLATFORM_ACTIONS.keys()) == expected_platforms

    def test_xiaohongshu_actions(self):
        actions = get_platform_actions("xiaohongshu")
        assert COLLECT_POST in actions
        assert SHARE_POST in actions

    def test_douyin_actions(self):
        actions = get_platform_actions("douyin")
        assert COLLECT_POST in actions

    def test_kuaishou_actions(self):
        actions = get_platform_actions("kuaishou")
        assert SEND_GIFT in actions
        assert POST_SHUOSHUO in actions

    def test_bilibili_actions(self):
        actions = get_platform_actions("bilibili")
        assert SEND_DANMAKU in actions
        assert GIVE_COIN in actions
        assert TRIPLE_TAP in actions

    def test_wechat_video_actions(self):
        actions = get_platform_actions("wechat_video")
        assert SHARE_TO_FRIENDS in actions

    def test_weibo_has_no_custom_actions(self):
        actions = get_platform_actions("weibo")
        assert actions == []


class TestIsCustomAction:
    def test_custom_action_returns_true(self):
        assert is_custom_action(COLLECT_POST) is True
        assert is_custom_action(SEND_DANMAKU) is True
        assert is_custom_action(TRIPLE_TAP) is True

    def test_core_action_returns_false(self):
        assert is_custom_action("create_post") is False
        assert is_custom_action("like_post") is False

    def test_unknown_action_returns_false(self):
        assert is_custom_action("teleport") is False


class TestGetPlatformActions:
    def test_unknown_platform_raises(self):
        with pytest.raises(KeyError, match="Unknown platform"):
            get_platform_actions("tiktok")
