"""Weibo platform adapter.

Weibo uses the same action set as Twitter but has a custom
recommendation algorithm that combines hot scores with
trending topic weighting.
"""

from __future__ import annotations

import heapq
import logging
import random
from datetime import datetime
from math import log
from typing import Any

from oasis.social_platform.platform import Platform
from oasis.social_platform.typing import RecsysType

from engine.platforms.base import BasePlatformAdapter
from engine.platforms.prompts.weibo import get_weibo_system_prompt

logger = logging.getLogger(__name__)


def _calculate_weibo_hot_score(
    num_likes: int,
    num_dislikes: int,
    num_shares: int,
    num_comments: int,
    created_at_str: str,
) -> float:
    """Compute a Weibo-style hot score for a post.

    Weibo's hot score gives extra weight to shares (reposts) and comments.
    """
    engagement = (
        num_likes - num_dislikes + 2 * num_shares + 1.5 * num_comments
    )
    order = log(max(abs(engagement), 1), 10)
    sign = 1 if engagement > 0 else -1 if engagement < 0 else 0

    try:
        created_at = datetime.strptime(created_at_str, "%Y-%m-%d %H:%M:%S.%f")
    except (ValueError, TypeError):
        try:
            created_at = datetime.strptime(created_at_str, "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            created_at = datetime.now()

    epoch = datetime(1970, 1, 1)
    td = created_at - epoch
    epoch_seconds = td.days * 86400 + td.seconds + float(td.microseconds) / 1e6
    seconds = epoch_seconds - 1134028003

    return round(sign * order + seconds / 45000, 7)


def rec_sys_weibo(
    post_table: list[dict[str, Any]],
    rec_matrix: list[list],
    max_rec_post_len: int,
    db_cursor: Any = None,
) -> list[list]:
    """Weibo recommendation system: hot score + trending topic weight."""
    post_ids = [post["post_id"] for post in post_table]

    if len(post_ids) <= max_rec_post_len:
        return [post_ids] * len(rec_matrix)

    comment_counts: dict[int, int] = {}
    if db_cursor is not None:
        for post in post_table:
            pid = post["post_id"]
            db_cursor.execute(
                "SELECT COUNT(*) FROM comment WHERE post_id = ?", (pid,)
            )
            row = db_cursor.fetchone()
            comment_counts[pid] = row[0] if row else 0

    scored_posts: list[tuple[float, int]] = []
    for post in post_table:
        pid = post["post_id"]
        num_comments = comment_counts.get(pid, 0)
        created_at_str = str(post.get("created_at", ""))
        score = _calculate_weibo_hot_score(
            num_likes=post.get("num_likes", 0),
            num_dislikes=post.get("num_dislikes", 0),
            num_shares=post.get("num_shares", 0),
            num_comments=num_comments,
            created_at_str=created_at_str,
        )
        scored_posts.append((score, pid))

    top_posts = heapq.nlargest(
        max_rec_post_len, scored_posts, key=lambda x: x[0]
    )
    top_post_ids = [pid for _, pid in top_posts]

    return [top_post_ids] * len(rec_matrix)


class WeiboPlatform(BasePlatformAdapter):
    """Weibo platform adapter.

    Uses the same action set as Twitter but with:
    - A hot-score recsys that weights reposts and comments more heavily
    - Chinese agent prompts capturing Weibo's 围观吃瓜 culture
    """

    PLATFORM_NAME = "weibo"
    CUSTOM_ACTIONS: dict[str, str] = {}

    def __init__(
        self,
        db_path: str,
        channel: Any = None,
        recsys_type: str | RecsysType = "reddit",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            db_path=db_path,
            channel=channel,
            recsys_type=recsys_type,
            **kwargs,
        )

    async def update_rec_table(self):
        """Override to use Weibo-specific recommendation algorithm."""
        from oasis.social_platform.database import (
            fetch_rec_table_as_matrix,
            fetch_table_from_db,
        )

        logger.info("Weibo: refreshing recommendation cache...")
        post_table = fetch_table_from_db(self.db_cursor, "post")
        rec_matrix = fetch_rec_table_as_matrix(self.db_cursor)

        new_rec_matrix = rec_sys_weibo(
            post_table,
            rec_matrix,
            self.max_rec_post_len,
            db_cursor=self.db_cursor,
        )

        self.pl_utils._execute_db_command("DELETE FROM rec", commit=True)

        insert_values = [
            (user_id, post_id)
            for user_id in range(len(new_rec_matrix))
            for post_id in new_rec_matrix[user_id]
        ]
        self.pl_utils._execute_many_db_command(
            "INSERT INTO rec (user_id, post_id) VALUES (?, ?)",
            insert_values,
            commit=True,
        )

    def get_system_prompt(
        self,
        name: str | None = None,
        bio: str | None = None,
        profile: dict[str, Any] | None = None,
    ) -> str:
        return get_weibo_system_prompt(name=name, bio=bio, profile=profile)


# Self-register with the global registry
from engine.platforms import registry as _registry

try:
    _registry.register(
        name="weibo",
        adapter_class=WeiboPlatform,
        default_recsys="reddit",
        default_actions=[
            "create_post", "like_post", "repost", "quote_post",
            "follow", "unfollow", "create_comment", "do_nothing",
        ],
        description="微博 - 中国最大的公共社交媒体平台",
    )
except ValueError:
    pass  # Already registered
