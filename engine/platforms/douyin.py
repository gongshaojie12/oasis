"""Douyin (TikTok China) platform adapter.

Adds one custom action:
- collect_post: Bookmark/collect a video post

Uses a traffic pool recommendation system that simulates Douyin's
tiered exposure model:
- Tier 1: New posts get shown to ~50 users (small pool)
- Tier 2: Posts with good engagement get shown to ~200 users
- Tier 3: Posts with excellent engagement get full distribution
"""

from __future__ import annotations

import logging
import random
from collections import defaultdict
from typing import Any

from oasis.social_platform.typing import RecsysType

from engine.platforms.actions import COLLECT_POST
from engine.platforms.base import BasePlatformAdapter
from engine.platforms.prompts.douyin import get_douyin_system_prompt

logger = logging.getLogger(__name__)


def _calculate_engagement_rate(post: dict[str, Any]) -> float:
    """Calculate engagement rate for a post.

    The engagement rate determines which traffic pool tier
    the post belongs to.

    Args:
        post: Post dict with num_likes, num_dislikes, num_shares.

    Returns:
        Engagement rate as a float.
    """
    likes = post.get("num_likes", 0)
    dislikes = post.get("num_dislikes", 0)
    shares = post.get("num_shares", 0)
    total_interactions = likes + dislikes + shares
    if total_interactions == 0:
        return 0.0
    positive = likes + shares
    return positive / total_interactions


def rec_sys_douyin(
    post_table: list[dict[str, Any]],
    rec_matrix: list[list],
    max_rec_post_len: int,
    tier1_size: int = 50,
    tier2_size: int = 200,
    tier1_threshold: float = 0.3,
    tier2_threshold: float = 0.6,
) -> list[list]:
    """Douyin traffic pool recommendation system.

    Simulates the tiered distribution model:
    - All new posts start in Tier 1 (shown to a small sample)
    - Posts exceeding tier1_threshold engagement move to Tier 2
    - Posts exceeding tier2_threshold engagement get full distribution
    - Full distribution posts are recommended to everyone

    The number of users in rec_matrix determines the pool sizes.
    If there are fewer users than the tier size, all users see
    the post.

    Args:
        post_table: List of post dicts.
        rec_matrix: Current recommendation matrix.
        max_rec_post_len: Maximum posts per user.
        tier1_size: Number of users in the initial exposure pool.
        tier2_size: Number of users in the mid-tier pool.
        tier1_threshold: Engagement rate to advance from tier 1 to 2.
        tier2_threshold: Engagement rate to advance to full distribution.

    Returns:
        Updated recommendation matrix.
    """
    post_ids = [post["post_id"] for post in post_table]
    num_users = len(rec_matrix)

    if len(post_ids) <= max_rec_post_len:
        return [post_ids] * num_users

    tier_full: list[int] = []
    tier_mid: list[int] = []
    tier_entry: list[int] = []

    for post in post_table:
        rate = _calculate_engagement_rate(post)
        if rate >= tier2_threshold:
            tier_full.append(post["post_id"])
        elif rate >= tier1_threshold:
            tier_mid.append(post["post_id"])
        else:
            tier_entry.append(post["post_id"])

    user_recs: dict[int, list[int]] = defaultdict(list)

    for pid in tier_full:
        for uid in range(num_users):
            user_recs[uid].append(pid)

    if tier_mid:
        mid_users = list(range(num_users))
        if len(mid_users) > tier2_size:
            mid_users = random.sample(mid_users, tier2_size)
        for pid in tier_mid:
            target = random.sample(mid_users, min(len(mid_users), tier2_size))
            for uid in target:
                user_recs[uid].append(pid)

    if tier_entry:
        entry_users = list(range(num_users))
        for pid in tier_entry:
            target_size = min(len(entry_users), tier1_size)
            target = random.sample(entry_users, target_size)
            for uid in target:
                user_recs[uid].append(pid)

    new_rec_matrix: list[list] = []
    for uid in range(num_users):
        recs = user_recs.get(uid, [])
        seen = set()
        unique_recs = []
        for pid in recs:
            if pid not in seen:
                seen.add(pid)
                unique_recs.append(pid)
        if len(unique_recs) > max_rec_post_len:
            unique_recs = unique_recs[:max_rec_post_len]
        elif len(unique_recs) < max_rec_post_len:
            remaining = [p for p in post_ids if p not in seen]
            fill = remaining[: max_rec_post_len - len(unique_recs)]
            unique_recs.extend(fill)
        new_rec_matrix.append(unique_recs)

    return new_rec_matrix


class DouyinPlatform(BasePlatformAdapter):
    """Douyin (TikTok China) platform adapter.

    Custom actions:
    - collect_post: Bookmark a short video post

    Custom recsys:
    - Traffic pool system (Tier 1: 50 users, Tier 2: 200, Tier 3: full)
    """

    PLATFORM_NAME = "douyin"
    CUSTOM_ACTIONS = {
        COLLECT_POST: "collect_post",
    }

    def _setup_custom_tables(self) -> None:
        """Create collection table for Douyin."""
        self.db_cursor.executescript("""
            CREATE TABLE IF NOT EXISTS collection (
                collection_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                post_id INTEGER,
                created_at DATETIME,
                FOREIGN KEY(user_id) REFERENCES user(user_id),
                FOREIGN KEY(post_id) REFERENCES post(post_id)
            );
        """)
        self.db.commit()

    async def running(self):
        """Override running loop to handle custom action strings."""
        from oasis.social_platform.typing import ActionType

        while True:
            message_id, data = await self.channel.receive_from()
            agent_id, message, action = data

            if action == ActionType.EXIT.value or action == "exit":
                import sqlite3

                if self.db_path == ":memory:":
                    dst = sqlite3.connect("mock.db")
                    with dst:
                        self.db.backup(dst)
                self.db_cursor.close()
                self.db.close()
                break

            action_function = getattr(self, action, None)
            if action_function:
                func_code = action_function.__code__
                param_names = func_code.co_varnames[:func_code.co_argcount]
                len_param_names = len(param_names)
                if len_param_names > 3:
                    raise ValueError(
                        f"Functions with {len_param_names} parameters "
                        f"are not supported."
                    )
                params = {}
                if len_param_names >= 2:
                    params["agent_id"] = agent_id
                if len_param_names == 3:
                    second_param_name = param_names[2]
                    params[second_param_name] = message
                result = await action_function(**params)
                await self.channel.send_to((message_id, agent_id, result))
            else:
                raise ValueError(f"Action {action} is not supported")

    async def collect_post(self, agent_id: int, post_id: int):
        """Collect (bookmark) a short video post.

        Args:
            agent_id: The collecting user's agent ID.
            post_id: The post to collect.

        Returns:
            Dict with success status and collection_id.
        """
        current_time = self._get_current_time()
        try:
            user_id = agent_id

            check_query = (
                "SELECT * FROM collection WHERE user_id = ? AND post_id = ?"
            )
            self.pl_utils._execute_db_command(check_query, (user_id, post_id))
            if self.db_cursor.fetchone():
                return {
                    "success": False,
                    "error": "Collection record already exists.",
                }

            insert_query = (
                "INSERT INTO collection (user_id, post_id, created_at) "
                "VALUES (?, ?, ?)"
            )
            self.pl_utils._execute_db_command(
                insert_query, (user_id, post_id, current_time), commit=True
            )
            collection_id = self.db_cursor.lastrowid

            self._record_custom_trace(
                user_id,
                COLLECT_POST,
                {"post_id": post_id, "collection_id": collection_id},
            )
            return {"success": True, "collection_id": collection_id}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def update_rec_table(self):
        """Override to use Douyin traffic pool recsys."""
        from oasis.social_platform.database import (
            fetch_rec_table_as_matrix,
            fetch_table_from_db,
        )

        logger.info("Douyin: refreshing recommendation cache...")
        post_table = fetch_table_from_db(self.db_cursor, "post")
        rec_matrix = fetch_rec_table_as_matrix(self.db_cursor)

        new_rec_matrix = rec_sys_douyin(
            post_table, rec_matrix, self.max_rec_post_len,
        )

        self.pl_utils._execute_db_command("DELETE FROM rec", commit=True)
        insert_values = [
            (user_id, post_id)
            for user_id in range(len(new_rec_matrix))
            for post_id in new_rec_matrix[user_id]
        ]
        self.pl_utils._execute_many_db_command(
            "INSERT INTO rec (user_id, post_id) VALUES (?, ?)",
            insert_values, commit=True,
        )

    def get_system_prompt(
        self,
        name: str | None = None,
        bio: str | None = None,
        profile: dict[str, Any] | None = None,
    ) -> str:
        return get_douyin_system_prompt(name=name, bio=bio, profile=profile)


# Self-register with the global registry
from engine.platforms import registry as _registry

try:
    _registry.register(
        name="douyin",
        adapter_class=DouyinPlatform,
        default_recsys="random",
        default_actions=[
            "create_post", "like_post", "collect_post",
            "follow", "create_comment", "do_nothing",
        ],
        description="抖音 - 中国最大的短视频平台",
    )
except ValueError:
    pass
