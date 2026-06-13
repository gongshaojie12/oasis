# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
from wanxiang.actions.l2_social import L2_ACTIONS, l2_action_names
from wanxiang.actions.layers import ActionLayer


def test_l2_has_core_social_actions():
    names = l2_action_names()
    expected = {"publish", "repost", "like", "dislike", "comment",
                "follow", "collect", "direct_message", "block"}
    assert expected <= names


def test_l2_actions_all_in_l2_layer():
    assert all(a.layer is ActionLayer.L2_SOCIAL for a in L2_ACTIONS)


def test_l2_comment_has_content_param():
    comment = next(a for a in L2_ACTIONS if a.name == "comment")
    assert "content" in comment.params


def test_l2_action_names_unique():
    names = [a.name for a in L2_ACTIONS]
    assert len(names) == len(set(names))


def test_l2_action_names_helper_returns_set():
    assert isinstance(l2_action_names(), set)
