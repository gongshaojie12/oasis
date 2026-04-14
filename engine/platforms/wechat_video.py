"""WeChat Video (微信视频号) platform adapter.

Adds one custom action:
- share_to_friends: Share a video to WeChat friends (social spread)

Uses a social-first recommendation system where friend likes
are the primary discovery mechanism, with algorithmic scoring
as a secondary signal.
"""

from __future__ import annotations

import heapq
import logging
import random
from collections import defaultdict
from typing import Any

from oasis.social_platform.typing import RecsysType

from engine.platforms.actions import SHARE_TO_FRIENDS
from engine.platforms.base import BasePlatformAdapter
from engine.platforms.prompts.wechat_video import (
    get_wechat_video_system_prompt,
)

logger = logging.getLogger(__name__)


def rec_sys_wechat_video(
    user_table: list[dict[str, Any]],
    post_table: list[dict[str, Any]],
    rec_matrix: list[list],
    max_rec_post_len: int,
    db_cursor: Any = None,
    friend_like_weight: float = 3.0,
    friend_share_weight: float = 4.0,
) -> list[list]:
    """WeChat Video social-first recommendation system.

    WeChat Video's algorithm prioritizes social signals:
    1. Posts liked by friends get 3x weight
    2. Posts shared by friends get 4x weight
    3. Base engagement provides secondary scoring

    This creates a "friend bubble" where you primarily see what
    your social circle interacts with.

    Args:
        user_table: List of user dicts.
        post_table: List of post dicts.
        rec_matrix: Current recommendation matrix.
        max_rec_post_len: Maximum posts per user.
        db_cursor: Database cursor for social data.
        friend_like_weight: Score multiplier for friend-liked posts.
        friend_share_weight: Score multiplier for friend-shared posts.

    Returns:
        Updated recommendation matrix.
    """
    post_ids = [post["post_id"] for post in post_table]
    num_users = len(rec_matrix)

    if len(post_ids) <= max_rec_post_len:
        return [post_ids] * num_users

    follow_map: dict[int, set[int]] = defaultdict(set)
    post_likers: dict[int, set[int]] = defaultdict(set)
    post_sharers: dict[int, set[int]] = defaultdict(set)

    if db_cursor is not None:
        db_cursor.execute("SELECT follower_id, followee_id FROM follow")
        for row in db_cursor.fetchall():
            follow_map[row[0]].add(row[1])
            follow_map[row[1]].add(row[0])

        db_cursor.execute("SELECT post_id, user_id FROM 'like'")
        for row in db_cursor.fetchall():
            post_likers[row[0]].add(row[1])

        try:
            db_cursor.execute(
                "SELECT post_id, user_id FROM friend_share"
            )
            for row in db_cursor.fetchall():
                post_sharers[row[0]].add(row[1])
        except Exception:
            pass

    base_scores: dict[int, float] = {}
    for post in post_table:
        pid = post["post_id"]
        likes = post.get("num_likes", 0)
        shares = post.get("num_shares", 0)
        base_scores[pid] = likes + shares * 1.5

    new_rec_matrix: list[list] = []
    for uid in range(num_users):
        friends = follow_map.get(uid, set())
        user_scored: list[tuple[float, int]] = []

        for post in post_table:
            pid = post["post_id"]
            score = base_scores[pid]

            likers = post_likers.get(pid, set())
            friend_likers = friends & likers
            if friend_likers:
                score += len(friend_likers) * friend_like_weight

            sharers = post_sharers.get(pid, set())
            friend_sharers = friends & sharers
            if friend_sharers:
                score += len(friend_sharers) * friend_share_weight

            score += random.uniform(0, 0.05)
            user_scored.append((score, pid))

        top_posts = heapq.nlargest(
            max_rec_post_len, user_scored, key=lambda x: x[0]
        )
        new_rec_matrix.append([pid for _, pid in top_posts])

    return new_rec_matrix


class WeChatVideoPlatform(BasePlatformAdapter):
    """WeChat Video (微信视频号) platform adapter.

    Custom actions:
    - share_to_friends: Share video to WeChat friends list

    Custom recsys:
    - Social-first: friend-likes and friend-shares as primary signals
    """

    PLATFORM_NAME = "wechat_video"
    CUSTOM_ACTIONS = {
        SHARE_TO_FRIENDS: "share_to_friends",
    }

    def _setup_custom_tables(self) -> None:
        """Create friend_share table for WeChat Video."""
        self.db_cursor.executescript("""
            CREATE TABLE IF NOT EXISTS friend_share (
                share_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                post_id INTEGER,
                target_user_id INTEGER,
                message TEXT DEFAULT '',
                created_at DATETIME,
                FOREIGN KEY(user_id) REFERENCES user(user_id),
                FOREIGN KEY(post_id) REFERENCES post(post_id),
                FOREIGN KEY(target_user_id) REFERENCES user(user_id)
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

    async def share_to_friends(self, agent_id: int, share_message: tuple):
        """Share a video to a specific WeChat friend.

        This is the primary distribution mechanism on WeChat Video.
        Content spreads through the social graph via direct shares.

        Args:
            agent_id: The sharing user's agent ID.
            share_message: Tuple of (post_id, target_user_id, message).
                The message is an optional recommendation text.

        Returns:
            Dict with success status and share_id.
        """
        post_id, target_user_id, rec_message = share_message
        current_time = self._get_current_time()
        try:
            user_id = agent_id

            if user_id == target_user_id:
                return {
                    "success": False,
                    "error": "Cannot share to yourself.",
                }

            post_check = "SELECT post_id FROM post WHERE post_id = ?"
            self.pl_utils._execute_db_command(post_check, (post_id,))
            if not self.db_cursor.fetchone():
                return {"success": False, "error": "Post not found."}

            user_check = "SELECT user_id FROM user WHERE user_id = ?"
            self.pl_utils._execute_db_command(user_check, (target_user_id,))
            if not self.db_cursor.fetchone():
                return {"success": False, "error": "Target user not found."}

            insert_query = (
                "INSERT INTO friend_share (user_id, post_id, "
                "target_user_id, message, created_at) "
                "VALUES (?, ?, ?, ?, ?)"
            )
            self.pl_utils._execute_db_command(
                insert_query,
                (user_id, post_id, target_user_id, rec_message, current_time),
                commit=True,
            )
            share_id = self.db_cursor.lastrowid

            update_query = (
                "UPDATE post SET num_shares = num_shares + 1 "
                "WHERE post_id = ?"
            )
            self.pl_utils._execute_db_command(
                update_query, (post_id,), commit=True
            )

            self._record_custom_trace(
                user_id,
                SHARE_TO_FRIENDS,
                {
                    "post_id": post_id,
                    "target_user_id": target_user_id,
                    "message": rec_message,
                    "share_id": share_id,
                },
            )
            return {
                "success": True,
                "share_id": share_id,
                "target_user_id": target_user_id,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def update_rec_table(self):
        """Override to use WeChat Video social-first recsys."""
        from oasis.social_platform.database import (
            fetch_rec_table_as_matrix,
            fetch_table_from_db,
        )

        logger.info("WeChat Video: refreshing recommendation cache...")
        user_table = fetch_table_from_db(self.db_cursor, "user")
        post_table = fetch_table_from_db(self.db_cursor, "post")
        rec_matrix = fetch_rec_table_as_matrix(self.db_cursor)

        new_rec_matrix = rec_sys_wechat_video(
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
        return get_wechat_video_system_prompt(
            name=name, bio=bio, profile=profile
        )


# Self-register with the global registry
from engine.platforms import registry as _registry

try:
    _registry.register(
        name="wechat_video",
        adapter_class=WeChatVideoPlatform,
        default_recsys="random",
        default_actions=[
            "create_post", "like_post", "share_to_friends",
            "follow", "create_comment", "do_nothing",
        ],
        description="微信视频号 - 微信生态内的短视频平台",
    )
except ValueError:
    pass
