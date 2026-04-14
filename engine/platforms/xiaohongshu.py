"""Xiaohongshu (Little Red Book) platform adapter.

Adds two custom actions:
- collect_post: Bookmark/collect a post (higher weight than likes)
- share_post: Share a post to friends/external

Uses a dual-channel recommendation system with collection-weighted ranking.
"""

from __future__ import annotations

import heapq
import logging
import random
from collections import defaultdict
from math import log
from typing import Any

from oasis.social_platform.typing import RecsysType

from engine.platforms.actions import COLLECT_POST, SHARE_POST
from engine.platforms.base import BasePlatformAdapter
from engine.platforms.prompts.xiaohongshu import get_xiaohongshu_system_prompt

logger = logging.getLogger(__name__)


def rec_sys_xiaohongshu(
    post_table: list[dict[str, Any]],
    rec_matrix: list[list],
    max_rec_post_len: int,
    db_cursor: Any = None,
) -> list[list]:
    """Xiaohongshu dual-channel recommendation system.

    Scoring: score = (collections*3 + likes*1 + shares*2) * recency_factor
    Collections are the strongest signal on Xiaohongshu.
    """
    post_ids = [post["post_id"] for post in post_table]

    if len(post_ids) <= max_rec_post_len:
        return [post_ids] * len(rec_matrix)

    collection_counts: dict[int, int] = defaultdict(int)
    share_counts: dict[int, int] = defaultdict(int)
    if db_cursor is not None:
        for post in post_table:
            pid = post["post_id"]
            db_cursor.execute(
                "SELECT COUNT(*) FROM collection WHERE post_id = ?", (pid,)
            )
            row = db_cursor.fetchone()
            if row:
                collection_counts[pid] = row[0]
            db_cursor.execute(
                "SELECT COUNT(*) FROM share WHERE post_id = ?", (pid,)
            )
            row = db_cursor.fetchone()
            if row:
                share_counts[pid] = row[0]

    scored_posts: list[tuple[float, int]] = []
    for i, post in enumerate(post_table):
        pid = post["post_id"]
        num_collections = collection_counts.get(pid, 0)
        num_shares_custom = share_counts.get(pid, 0)
        num_likes = post.get("num_likes", 0)
        num_shares_core = post.get("num_shares", 0)

        engagement = (
            num_collections * 3.0
            + num_likes * 1.0
            + (num_shares_core + num_shares_custom) * 2.0
        )

        total_posts = len(post_table)
        recency = 1.0 + 0.5 * (i / max(total_posts - 1, 1))

        score = engagement * recency
        scored_posts.append((score, pid))

    top_posts = heapq.nlargest(
        max_rec_post_len, scored_posts, key=lambda x: x[0]
    )
    top_post_ids = [pid for _, pid in top_posts]

    new_rec_matrix: list[list] = []
    for _ in range(len(rec_matrix)):
        user_recs = list(top_post_ids)
        num_to_shuffle = max(1, len(user_recs) // 5)
        tail = user_recs[-num_to_shuffle:]
        random.shuffle(tail)
        user_recs[-num_to_shuffle:] = tail
        new_rec_matrix.append(user_recs)

    return new_rec_matrix


class XiaohongshuPlatform(BasePlatformAdapter):
    """Xiaohongshu platform adapter with collect_post and share_post."""

    PLATFORM_NAME = "xiaohongshu"
    CUSTOM_ACTIONS = {
        COLLECT_POST: "collect_post",
        SHARE_POST: "share_post",
    }

    def _setup_custom_tables(self) -> None:
        """Create collection and share tables."""
        self.db_cursor.executescript("""
            CREATE TABLE IF NOT EXISTS collection (
                collection_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                post_id INTEGER,
                created_at DATETIME,
                FOREIGN KEY(user_id) REFERENCES user(user_id),
                FOREIGN KEY(post_id) REFERENCES post(post_id)
            );
            CREATE TABLE IF NOT EXISTS share (
                share_id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        """Collect (bookmark) a post."""
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

    async def share_post(self, agent_id: int, post_id: int):
        """Share a post to friends or external platforms."""
        current_time = self._get_current_time()
        try:
            user_id = agent_id
            post_check = "SELECT post_id FROM post WHERE post_id = ?"
            self.pl_utils._execute_db_command(post_check, (post_id,))
            if not self.db_cursor.fetchone():
                return {"success": False, "error": "Post not found."}
            insert_query = (
                "INSERT INTO share (user_id, post_id, created_at) "
                "VALUES (?, ?, ?)"
            )
            self.pl_utils._execute_db_command(
                insert_query, (user_id, post_id, current_time), commit=True
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
                SHARE_POST,
                {"post_id": post_id, "share_id": share_id},
            )
            return {"success": True, "share_id": share_id}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def update_rec_table(self):
        """Override to use Xiaohongshu-specific recsys."""
        from oasis.social_platform.database import (
            fetch_rec_table_as_matrix,
            fetch_table_from_db,
        )
        logger.info("Xiaohongshu: refreshing recommendation cache...")
        post_table = fetch_table_from_db(self.db_cursor, "post")
        rec_matrix = fetch_rec_table_as_matrix(self.db_cursor)
        new_rec_matrix = rec_sys_xiaohongshu(
            post_table, rec_matrix, self.max_rec_post_len,
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
        return get_xiaohongshu_system_prompt(name=name, bio=bio, profile=profile)


# Self-register with the global registry
from engine.platforms import registry as _registry

try:
    _registry.register(
        name="xiaohongshu",
        adapter_class=XiaohongshuPlatform,
        default_recsys="random",
        default_actions=[
            "create_post", "like_post", "collect_post", "share_post",
            "follow", "create_comment", "do_nothing",
        ],
        description="小红书 - 中国最大的种草社区和生活方式平台",
    )
except ValueError:
    pass
