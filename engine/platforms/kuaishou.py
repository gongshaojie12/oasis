"""Kuaishou platform adapter.

Adds two custom actions:
- send_gift: Send a virtual gift to a post creator (livestream tipping)
- post_shuoshuo: Post a "说说" (status update, like stories)

Uses a social + algorithm mixed recommendation system where
content from followed users gets priority weighting.
"""

from __future__ import annotations

import heapq
import logging
import random
from collections import defaultdict
from typing import Any

from oasis.social_platform.typing import RecsysType

from engine.platforms.actions import POST_SHUOSHUO, SEND_GIFT
from engine.platforms.base import BasePlatformAdapter
from engine.platforms.prompts.kuaishou import get_kuaishou_system_prompt

logger = logging.getLogger(__name__)


def rec_sys_kuaishou(
    user_table: list[dict[str, Any]],
    post_table: list[dict[str, Any]],
    rec_matrix: list[list],
    max_rec_post_len: int,
    follow_weight: float = 2.0,
    db_cursor: Any = None,
) -> list[list]:
    """Kuaishou social + algorithm mixed recommendation system.

    Kuaishou's recommendation blends social signals (followed users'
    content) with algorithmic scoring. Posts from followed users get
    a weight multiplier, making the follow-page more prominent than
    pure algorithmic platforms like Douyin.

    Args:
        user_table: List of user dicts.
        post_table: List of post dicts.
        rec_matrix: Current recommendation matrix.
        max_rec_post_len: Maximum posts per user.
        follow_weight: Multiplier for posts from followed users.
        db_cursor: Database cursor for follow relationship lookup.

    Returns:
        Updated recommendation matrix.
    """
    post_ids = [post["post_id"] for post in post_table]
    num_users = len(rec_matrix)

    if len(post_ids) <= max_rec_post_len:
        return [post_ids] * num_users

    follow_map: dict[int, set[int]] = defaultdict(set)
    if db_cursor is not None:
        db_cursor.execute("SELECT follower_id, followee_id FROM follow")
        for row in db_cursor.fetchall():
            follow_map[row[0]].add(row[1])

    post_scores: dict[int, float] = {}
    for post in post_table:
        pid = post["post_id"]
        likes = post.get("num_likes", 0)
        shares = post.get("num_shares", 0)
        score = likes + shares * 1.5
        post_scores[pid] = score

    new_rec_matrix: list[list] = []
    for uid in range(num_users):
        following = follow_map.get(uid, set())
        user_scored: list[tuple[float, int]] = []

        for post in post_table:
            pid = post["post_id"]
            base_score = post_scores[pid]
            if post["user_id"] in following:
                final_score = base_score * follow_weight
            else:
                final_score = base_score
            final_score += random.uniform(0, 0.1)
            user_scored.append((final_score, pid))

        top_posts = heapq.nlargest(
            max_rec_post_len, user_scored, key=lambda x: x[0]
        )
        new_rec_matrix.append([pid for _, pid in top_posts])

    return new_rec_matrix


class KuaishouPlatform(BasePlatformAdapter):
    """Kuaishou platform adapter.

    Custom actions:
    - send_gift: Send virtual gift to content creator
    - post_shuoshuo: Post a status update (说说)

    Custom recsys:
    - Social + algo mix with follow-page weighting
    """

    PLATFORM_NAME = "kuaishou"
    CUSTOM_ACTIONS = {
        SEND_GIFT: "send_gift",
        POST_SHUOSHUO: "post_shuoshuo",
    }

    def _setup_custom_tables(self) -> None:
        """Create gift and shuoshuo tables for Kuaishou."""
        self.db_cursor.executescript("""
            CREATE TABLE IF NOT EXISTS gift (
                gift_id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER,
                receiver_id INTEGER,
                post_id INTEGER,
                gift_value INTEGER DEFAULT 1,
                created_at DATETIME,
                FOREIGN KEY(sender_id) REFERENCES user(user_id),
                FOREIGN KEY(receiver_id) REFERENCES user(user_id),
                FOREIGN KEY(post_id) REFERENCES post(post_id)
            );
            CREATE TABLE IF NOT EXISTS shuoshuo (
                shuoshuo_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                content TEXT,
                created_at DATETIME,
                FOREIGN KEY(user_id) REFERENCES user(user_id)
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

    async def send_gift(self, agent_id: int, gift_message: tuple):
        """Send a virtual gift to a post's creator.

        Args:
            agent_id: The gift sender's agent ID.
            gift_message: Tuple of (post_id, gift_value).

        Returns:
            Dict with success status and gift_id.
        """
        post_id, gift_value = gift_message
        current_time = self._get_current_time()
        try:
            user_id = agent_id

            post_query = "SELECT user_id FROM post WHERE post_id = ?"
            self.pl_utils._execute_db_command(post_query, (post_id,))
            post_row = self.db_cursor.fetchone()
            if not post_row:
                return {"success": False, "error": "Post not found."}
            receiver_id = post_row[0]

            if receiver_id == user_id:
                return {
                    "success": False,
                    "error": "Cannot send gift to yourself.",
                }

            insert_query = (
                "INSERT INTO gift (sender_id, receiver_id, post_id, "
                "gift_value, created_at) VALUES (?, ?, ?, ?, ?)"
            )
            self.pl_utils._execute_db_command(
                insert_query,
                (user_id, receiver_id, post_id, gift_value, current_time),
                commit=True,
            )
            gift_id = self.db_cursor.lastrowid

            self._record_custom_trace(
                user_id,
                SEND_GIFT,
                {
                    "post_id": post_id,
                    "receiver_id": receiver_id,
                    "gift_value": gift_value,
                    "gift_id": gift_id,
                },
            )
            return {
                "success": True,
                "gift_id": gift_id,
                "receiver_id": receiver_id,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def post_shuoshuo(self, agent_id: int, content: str):
        """Post a "说说" (status update / story).

        Shuoshuo are short-lived status updates similar to WeChat
        Moments or Instagram Stories -- primarily visible to followers.

        Args:
            agent_id: The posting user's agent ID.
            content: The shuoshuo text content.

        Returns:
            Dict with success status and shuoshuo_id.
        """
        current_time = self._get_current_time()
        try:
            user_id = agent_id

            insert_query = (
                "INSERT INTO shuoshuo (user_id, content, created_at) "
                "VALUES (?, ?, ?)"
            )
            self.pl_utils._execute_db_command(
                insert_query, (user_id, content, current_time), commit=True
            )
            shuoshuo_id = self.db_cursor.lastrowid

            self._record_custom_trace(
                user_id,
                POST_SHUOSHUO,
                {"content": content, "shuoshuo_id": shuoshuo_id},
            )
            return {"success": True, "shuoshuo_id": shuoshuo_id}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def update_rec_table(self):
        """Override to use Kuaishou social+algo recsys."""
        from oasis.social_platform.database import (
            fetch_rec_table_as_matrix,
            fetch_table_from_db,
        )

        logger.info("Kuaishou: refreshing recommendation cache...")
        user_table = fetch_table_from_db(self.db_cursor, "user")
        post_table = fetch_table_from_db(self.db_cursor, "post")
        rec_matrix = fetch_rec_table_as_matrix(self.db_cursor)

        new_rec_matrix = rec_sys_kuaishou(
            user_table, post_table, rec_matrix, self.max_rec_post_len,
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
            insert_values, commit=True,
        )

    def get_system_prompt(
        self,
        name: str | None = None,
        bio: str | None = None,
        profile: dict[str, Any] | None = None,
    ) -> str:
        return get_kuaishou_system_prompt(name=name, bio=bio, profile=profile)


# Self-register with the global registry
from engine.platforms import registry as _registry

try:
    _registry.register(
        name="kuaishou",
        adapter_class=KuaishouPlatform,
        default_recsys="random",
        default_actions=[
            "create_post", "like_post", "send_gift", "post_shuoshuo",
            "follow", "create_comment", "do_nothing",
        ],
        description="快手 - 真实接地气的短视频和直播平台",
    )
except ValueError:
    pass
