"""Base adapter class for Chinese social media platform extensions."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from oasis.social_platform.channel import Channel
from oasis.social_platform.platform import Platform
from oasis.social_platform.typing import RecsysType

logger = logging.getLogger(__name__)


class BasePlatformAdapter(Platform):
    """Base class for all Chinese social media platform adapters.

    Subclasses should:
    1. Define PLATFORM_NAME as a class attribute.
    2. Define CUSTOM_ACTIONS as a dict mapping action string names to
       their handler method names.
    3. Override custom_recsys() for platform-specific recommendation logic.
    4. Override get_system_prompt() for Chinese-language agent prompts.
    """

    PLATFORM_NAME: str = "base"
    CUSTOM_ACTIONS: dict[str, str] = {}

    def __init__(
        self,
        db_path: str,
        channel: Any = None,
        recsys_type: str | RecsysType = "random",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            db_path=db_path,
            channel=channel,
            recsys_type=recsys_type,
            **kwargs,
        )
        self._setup_custom_tables()

    def _setup_custom_tables(self) -> None:
        """Create any additional SQLite tables needed by this platform.
        Override in subclasses.
        """
        pass

    def _get_current_time(self) -> Any:
        """Return the current simulation time."""
        if self.recsys_type == RecsysType.REDDIT:
            return self.sandbox_clock.time_transfer(
                datetime.now(), self.start_time
            )
        return self.sandbox_clock.get_time_step()

    def _record_custom_trace(
        self,
        user_id: int,
        action: str,
        info: dict[str, Any],
    ) -> None:
        """Record a trace entry for a custom action."""
        current_time = self._get_current_time()
        trace_insert_query = (
            "INSERT INTO trace (user_id, created_at, action, info) "
            "VALUES (?, ?, ?, ?)"
        )
        action_info_str = json.dumps(info)
        self.pl_utils._execute_db_command(
            trace_insert_query,
            (user_id, current_time, action, action_info_str),
            commit=True,
        )

    def get_system_prompt(
        self,
        name: str | None = None,
        bio: str | None = None,
        profile: dict[str, Any] | None = None,
    ) -> str:
        name_str = f"你的名字是{name}。" if name else ""
        bio_str = f"你的简介：{bio}" if bio else ""
        return (
            f"# 目标\n你是一个社交媒体用户。\n\n"
            f"# 自我描述\n{name_str}\n{bio_str}\n\n"
            f"# 回复方式\n请通过工具调用来执行操作。"
        )

    def get_available_actions(self) -> list[str]:
        core_actions = [
            "create_post", "like_post", "repost", "quote_post",
            "follow", "unfollow", "create_comment", "refresh",
            "search_posts", "search_user", "trend", "do_nothing",
        ]
        custom = list(self.CUSTOM_ACTIONS.keys())
        return core_actions + custom
