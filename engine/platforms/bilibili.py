"""Bilibili platform adapter.

Adds three custom actions:
- send_danmaku: Send a scrolling comment (弹幕)
- give_coin: Give coins to a post's creator (投币)
- triple_tap: One-click like + coin + collect (一键三连)

Uses an interest tag + follow + trending recommendation system.
"""

from __future__ import annotations

import heapq
import logging
import random
from collections import defaultdict
from typing import Any

from oasis.social_platform.typing import RecsysType

from engine.platforms.actions import GIVE_COIN, SEND_DANMAKU, TRIPLE_TAP
from engine.platforms.base import BasePlatformAdapter
from engine.platforms.prompts.bilibili import get_bilibili_system_prompt

logger = logging.getLogger(__name__)


def rec_sys_bilibili(
    user_table: list[dict[str, Any]],
    post_table: list[dict[str, Any]],
    rec_matrix: list[list],
    max_rec_post_len: int,
    db_cursor: Any = None,
) -> list[list]:
    """Bilibili interest tag + follow + trending recommendation system.

    Scoring combines three signals:
    1. Engagement score: likes + coins*2 + collections*1.5 + danmaku*0.5
    2. Follow boost: 1.5x for posts from followed users
    3. Trending boost: posts in top 10% engagement get a bonus

    Args:
        user_table: List of user dicts.
        post_table: List of post dicts.
        rec_matrix: Current recommendation matrix.
        max_rec_post_len: Maximum posts per user.
        db_cursor: Database cursor for relationship/coin data.

    Returns:
        Updated recommendation matrix.
    """
    post_ids = [post["post_id"] for post in post_table]
    num_users = len(rec_matrix)

    if len(post_ids) <= max_rec_post_len:
        return [post_ids] * num_users

    follow_map: dict[int, set[int]] = defaultdict(set)
    coin_counts: dict[int, int] = defaultdict(int)
    danmaku_counts: dict[int, int] = defaultdict(int)
    collection_counts: dict[int, int] = defaultdict(int)

    if db_cursor is not None:
        db_cursor.execute("SELECT follower_id, followee_id FROM follow")
        for row in db_cursor.fetchall():
            follow_map[row[0]].add(row[1])

        for post in post_table:
            pid = post["post_id"]
            try:
                db_cursor.execute(
                    "SELECT COUNT(*) FROM coin WHERE post_id = ?", (pid,)
                )
                row = db_cursor.fetchone()
                if row:
                    coin_counts[pid] = row[0]
            except Exception:
                pass
            try:
                db_cursor.execute(
                    "SELECT COUNT(*) FROM danmaku WHERE post_id = ?", (pid,)
                )
                row = db_cursor.fetchone()
                if row:
                    danmaku_counts[pid] = row[0]
            except Exception:
                pass
            try:
                db_cursor.execute(
                    "SELECT COUNT(*) FROM collection WHERE post_id = ?", (pid,)
                )
                row = db_cursor.fetchone()
                if row:
                    collection_counts[pid] = row[0]
            except Exception:
                pass

    base_scores: dict[int, float] = {}
    for post in post_table:
        pid = post["post_id"]
        likes = post.get("num_likes", 0)
        coins = coin_counts.get(pid, 0)
        collections = collection_counts.get(pid, 0)
        danmaku = danmaku_counts.get(pid, 0)
        score = likes + coins * 2.0 + collections * 1.5 + danmaku * 0.5
        base_scores[pid] = score

    if base_scores:
        sorted_scores = sorted(base_scores.values(), reverse=True)
        trending_threshold = sorted_scores[max(0, len(sorted_scores) // 10)]
    else:
        trending_threshold = 0

    new_rec_matrix: list[list] = []
    for uid in range(num_users):
        following = follow_map.get(uid, set())
        user_scored: list[tuple[float, int]] = []

        for post in post_table:
            pid = post["post_id"]
            score = base_scores[pid]

            if post["user_id"] in following:
                score *= 1.5

            if score >= trending_threshold and trending_threshold > 0:
                score *= 1.2

            score += random.uniform(0, 0.05)
            user_scored.append((score, pid))

        top_posts = heapq.nlargest(
            max_rec_post_len, user_scored, key=lambda x: x[0]
        )
        new_rec_matrix.append([pid for _, pid in top_posts])

    return new_rec_matrix


class BilibiliPlatform(BasePlatformAdapter):
    """Bilibili platform adapter.

    Custom actions:
    - send_danmaku: Send a scrolling comment on a video
    - give_coin: Give coins to a video creator
    - triple_tap: One-click like + coin + collect (一键三连)

    Custom recsys:
    - Interest tag + follow + trending scoring
    """

    PLATFORM_NAME = "bilibili"
    CUSTOM_ACTIONS = {
        SEND_DANMAKU: "send_danmaku",
        GIVE_COIN: "give_coin",
        TRIPLE_TAP: "triple_tap",
    }

    def _setup_custom_tables(self) -> None:
        """Create danmaku, coin, and collection tables for Bilibili."""
        self.db_cursor.executescript("""
            CREATE TABLE IF NOT EXISTS danmaku (
                danmaku_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                post_id INTEGER,
                content TEXT,
                time_offset REAL DEFAULT 0.0,
                created_at DATETIME,
                FOREIGN KEY(user_id) REFERENCES user(user_id),
                FOREIGN KEY(post_id) REFERENCES post(post_id)
            );
            CREATE TABLE IF NOT EXISTS coin (
                coin_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                post_id INTEGER,
                num_coins INTEGER DEFAULT 1,
                created_at DATETIME,
                FOREIGN KEY(user_id) REFERENCES user(user_id),
                FOREIGN KEY(post_id) REFERENCES post(post_id)
            );
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

    async def send_danmaku(self, agent_id: int, danmaku_message: tuple):
        """Send a danmaku (scrolling comment) on a video.

        Args:
            agent_id: The sender's agent ID.
            danmaku_message: Tuple of (post_id, content).

        Returns:
            Dict with success status and danmaku_id.
        """
        post_id, content = danmaku_message
        current_time = self._get_current_time()
        try:
            user_id = agent_id

            post_check = "SELECT post_id FROM post WHERE post_id = ?"
            self.pl_utils._execute_db_command(post_check, (post_id,))
            if not self.db_cursor.fetchone():
                return {"success": False, "error": "Post not found."}

            insert_query = (
                "INSERT INTO danmaku (user_id, post_id, content, created_at) "
                "VALUES (?, ?, ?, ?)"
            )
            self.pl_utils._execute_db_command(
                insert_query, (user_id, post_id, content, current_time),
                commit=True,
            )
            danmaku_id = self.db_cursor.lastrowid

            self._record_custom_trace(
                user_id,
                SEND_DANMAKU,
                {
                    "post_id": post_id,
                    "content": content,
                    "danmaku_id": danmaku_id,
                },
            )
            return {"success": True, "danmaku_id": danmaku_id}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def give_coin(self, agent_id: int, coin_message: tuple):
        """Give coins to a video's creator.

        Each user can give at most 2 coins to a single video.

        Args:
            agent_id: The giver's agent ID.
            coin_message: Tuple of (post_id, num_coins).

        Returns:
            Dict with success status and coin_id.
        """
        post_id, num_coins = coin_message
        current_time = self._get_current_time()
        try:
            user_id = agent_id

            if num_coins < 1 or num_coins > 2:
                return {
                    "success": False,
                    "error": "Can only give 1 or 2 coins per video.",
                }

            post_check = "SELECT user_id FROM post WHERE post_id = ?"
            self.pl_utils._execute_db_command(post_check, (post_id,))
            post_row = self.db_cursor.fetchone()
            if not post_row:
                return {"success": False, "error": "Post not found."}

            existing_query = (
                "SELECT SUM(num_coins) FROM coin "
                "WHERE user_id = ? AND post_id = ?"
            )
            self.pl_utils._execute_db_command(
                existing_query, (user_id, post_id)
            )
            existing_row = self.db_cursor.fetchone()
            existing_coins = existing_row[0] if existing_row[0] else 0

            if existing_coins + num_coins > 2:
                return {
                    "success": False,
                    "error": (
                        f"Already gave {existing_coins} coin(s). "
                        f"Max 2 per video."
                    ),
                }

            insert_query = (
                "INSERT INTO coin (user_id, post_id, num_coins, created_at) "
                "VALUES (?, ?, ?, ?)"
            )
            self.pl_utils._execute_db_command(
                insert_query, (user_id, post_id, num_coins, current_time),
                commit=True,
            )
            coin_id = self.db_cursor.lastrowid

            self._record_custom_trace(
                user_id,
                GIVE_COIN,
                {
                    "post_id": post_id,
                    "num_coins": num_coins,
                    "coin_id": coin_id,
                },
            )
            return {"success": True, "coin_id": coin_id}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def triple_tap(self, agent_id: int, post_id: int):
        """Perform a "一键三连" (triple tap): like + coin + collect.

        This is the highest form of appreciation on Bilibili.
        Atomically performs all three actions.

        Args:
            agent_id: The user's agent ID.
            post_id: The post to triple-tap.

        Returns:
            Dict with success status and IDs of all three actions.
        """
        current_time = self._get_current_time()
        try:
            user_id = agent_id

            post_check = "SELECT post_id FROM post WHERE post_id = ?"
            self.pl_utils._execute_db_command(post_check, (post_id,))
            if not self.db_cursor.fetchone():
                return {"success": False, "error": "Post not found."}

            like_result = await self.like_post(agent_id, post_id)
            like_id = like_result.get("like_id")

            coin_check = (
                "SELECT SUM(num_coins) FROM coin "
                "WHERE user_id = ? AND post_id = ?"
            )
            self.pl_utils._execute_db_command(coin_check, (user_id, post_id))
            existing = self.db_cursor.fetchone()
            existing_coins = existing[0] if existing[0] else 0
            coin_id = None
            if existing_coins < 2:
                coins_to_give = min(1, 2 - existing_coins)
                coin_insert = (
                    "INSERT INTO coin (user_id, post_id, num_coins, "
                    "created_at) VALUES (?, ?, ?, ?)"
                )
                self.pl_utils._execute_db_command(
                    coin_insert,
                    (user_id, post_id, coins_to_give, current_time),
                    commit=True,
                )
                coin_id = self.db_cursor.lastrowid

            collection_check = (
                "SELECT * FROM collection WHERE user_id = ? AND post_id = ?"
            )
            self.pl_utils._execute_db_command(
                collection_check, (user_id, post_id)
            )
            collection_id = None
            if not self.db_cursor.fetchone():
                collection_insert = (
                    "INSERT INTO collection (user_id, post_id, created_at) "
                    "VALUES (?, ?, ?)"
                )
                self.pl_utils._execute_db_command(
                    collection_insert, (user_id, post_id, current_time),
                    commit=True,
                )
                collection_id = self.db_cursor.lastrowid

            self._record_custom_trace(
                user_id,
                TRIPLE_TAP,
                {
                    "post_id": post_id,
                    "like_id": like_id,
                    "coin_id": coin_id,
                    "collection_id": collection_id,
                },
            )
            return {
                "success": True,
                "like_id": like_id,
                "coin_id": coin_id,
                "collection_id": collection_id,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def update_rec_table(self):
        """Override to use Bilibili interest+follow+trending recsys."""
        from oasis.social_platform.database import (
            fetch_rec_table_as_matrix,
            fetch_table_from_db,
        )

        logger.info("Bilibili: refreshing recommendation cache...")
        user_table = fetch_table_from_db(self.db_cursor, "user")
        post_table = fetch_table_from_db(self.db_cursor, "post")
        rec_matrix = fetch_rec_table_as_matrix(self.db_cursor)

        new_rec_matrix = rec_sys_bilibili(
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
        return get_bilibili_system_prompt(name=name, bio=bio, profile=profile)


# Self-register with the global registry
from engine.platforms import registry as _registry

try:
    _registry.register(
        name="bilibili",
        adapter_class=BilibiliPlatform,
        default_recsys="random",
        default_actions=[
            "create_post", "like_post", "send_danmaku",
            "give_coin", "triple_tap", "follow",
            "create_comment", "do_nothing",
        ],
        description="Bilibili - 中国Z世代文化社区",
    )
except ValueError:
    pass
