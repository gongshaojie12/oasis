# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""L2 通用社交动作（跨平台抽象语义，不绑定任何具体平台）。

L3 平台方言把这些抽象动作映射为具体平台的叫法/规则。
"""
from __future__ import annotations

from wanxiang.actions.l1_decision import ActionSpec
from wanxiang.actions.layers import ActionLayer

L2_ACTIONS: tuple[ActionSpec, ...] = (
    ActionSpec("publish", ActionLayer.L2_SOCIAL, ("content",), "发布内容"),
    ActionSpec("repost", ActionLayer.L2_SOCIAL, ("target_id",), "转发扩散"),
    ActionSpec("like", ActionLayer.L2_SOCIAL, ("target_id",), "正向反馈"),
    ActionSpec("dislike", ActionLayer.L2_SOCIAL, ("target_id",), "负向反馈"),
    ActionSpec("comment", ActionLayer.L2_SOCIAL, ("target_id", "content"), "评论"),
    ActionSpec("follow", ActionLayer.L2_SOCIAL, ("target_user",), "关注/建立关系"),
    ActionSpec("collect", ActionLayer.L2_SOCIAL, ("target_id",), "收藏留存"),
    ActionSpec("direct_message", ActionLayer.L2_SOCIAL, ("target_user", "content"),
               "私信"),
    ActionSpec("block", ActionLayer.L2_SOCIAL, ("target_user",), "屏蔽"),
)


def l2_action_names() -> set[str]:
    return {a.name for a in L2_ACTIONS}
