"""Custom action type constants for Chinese social media platforms.

These are defined as string constants rather than extending the
oasis ActionType enum, since we do not modify oasis/ code. The
Platform.running() dispatch uses getattr(self, action.value), so
custom actions work as long as:
1. The action string is sent through the Channel
2. A method with the matching name exists on the Platform subclass
"""

# -- Xiaohongshu-specific actions --
COLLECT_POST = "collect_post"
SHARE_POST = "share_post"

# -- Douyin-specific actions --
# Uses COLLECT_POST from above (same semantics)

# -- Kuaishou-specific actions --
SEND_GIFT = "send_gift"
POST_SHUOSHUO = "post_shuoshuo"

# -- Bilibili-specific actions --
SEND_DANMAKU = "send_danmaku"
GIVE_COIN = "give_coin"
TRIPLE_TAP = "triple_tap"

# -- WeChat Video-specific actions --
SHARE_TO_FRIENDS = "share_to_friends"

# Complete mapping of all custom actions to their platform origin
PLATFORM_ACTIONS: dict[str, list[str]] = {
    "weibo": [],
    "xiaohongshu": [COLLECT_POST, SHARE_POST],
    "douyin": [COLLECT_POST],
    "kuaishou": [SEND_GIFT, POST_SHUOSHUO],
    "bilibili": [SEND_DANMAKU, GIVE_COIN, TRIPLE_TAP],
    "wechat_video": [SHARE_TO_FRIENDS],
}

ALL_CUSTOM_ACTIONS: set[str] = {
    COLLECT_POST,
    SHARE_POST,
    SEND_GIFT,
    POST_SHUOSHUO,
    SEND_DANMAKU,
    GIVE_COIN,
    TRIPLE_TAP,
    SHARE_TO_FRIENDS,
}


def is_custom_action(action_str: str) -> bool:
    """Check whether an action string is a custom platform action."""
    return action_str in ALL_CUSTOM_ACTIONS


def get_platform_actions(platform_name: str) -> list[str]:
    """Return the list of custom actions for a given platform."""
    if platform_name not in PLATFORM_ACTIONS:
        raise KeyError(
            f"Unknown platform '{platform_name}'. "
            f"Known: {', '.join(PLATFORM_ACTIONS.keys())}"
        )
    return PLATFORM_ACTIONS[platform_name]
