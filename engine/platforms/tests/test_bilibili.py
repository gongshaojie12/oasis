"""Tests for the Bilibili platform adapter."""

import os
import os.path as osp
import sqlite3

import pytest

from engine.platforms.bilibili import (
    BilibiliPlatform,
    rec_sys_bilibili,
)
from engine.platforms.prompts.bilibili import get_bilibili_system_prompt

parent_folder = osp.dirname(osp.abspath(__file__))
test_db_filepath = osp.join(parent_folder, "test_bilibili.db")


class TestBilibiliRecsys:
    def test_few_posts_returns_all(self):
        user_table = [{"user_id": 0}]
        post_table = [
            {"post_id": 1, "user_id": 0, "num_likes": 10, "num_shares": 0},
        ]
        rec_matrix = [[]]
        result = rec_sys_bilibili(
            user_table, post_table, rec_matrix, max_rec_post_len=5
        )
        assert len(result) == 1
        assert 1 in result[0]

    def test_top_k_selection(self):
        user_table = [{"user_id": 0}, {"user_id": 1}]
        post_table = [
            {"post_id": i, "user_id": i % 2, "num_likes": i * 5,
             "num_shares": 0}
            for i in range(1, 15)
        ]
        rec_matrix = [[], []]
        result = rec_sys_bilibili(
            user_table, post_table, rec_matrix, max_rec_post_len=3
        )
        assert len(result) == 2
        for row in result:
            assert len(row) == 3


class TestBilibiliPlatform:
    @pytest.fixture
    def platform(self):
        if os.path.exists(test_db_filepath):
            os.remove(test_db_filepath)
        p = BilibiliPlatform(db_path=test_db_filepath, recsys_type="random")
        yield p
        p.db_cursor.close()
        p.db.close()
        if os.path.exists(test_db_filepath):
            os.remove(test_db_filepath)

    def test_platform_name(self, platform):
        assert platform.PLATFORM_NAME == "bilibili"

    def test_custom_tables_created(self, platform):
        for table_name in ["danmaku", "coin", "collection"]:
            platform.db_cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                f"AND name='{table_name}'"
            )
            assert platform.db_cursor.fetchone() is not None, (
                f"Table {table_name} was not created"
            )

    @pytest.mark.asyncio
    async def test_send_danmaku(self, platform):
        conn = sqlite3.connect(test_db_filepath)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (1, 1, "bili_user", 0, 0),
        )
        cursor.execute(
            "INSERT INTO post (post_id, user_id, content, created_at, "
            "num_likes, num_dislikes, num_shares) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, 1, "B站视频", "2025-01-01 12:00:00", 0, 0, 0),
        )
        conn.commit()
        conn.close()

        result = await platform.send_danmaku(1, (1, "awsl"))
        assert result["success"] is True
        assert "danmaku_id" in result

    @pytest.mark.asyncio
    async def test_send_danmaku_nonexistent_post(self, platform):
        conn = sqlite3.connect(test_db_filepath)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (1, 1, "bili_user", 0, 0),
        )
        conn.commit()
        conn.close()

        result = await platform.send_danmaku(1, (999, "test"))
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_give_coin(self, platform):
        conn = sqlite3.connect(test_db_filepath)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (1, 1, "bili_user", 0, 0),
        )
        cursor.execute(
            "INSERT INTO post (post_id, user_id, content, created_at, "
            "num_likes, num_dislikes, num_shares) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, 1, "优质视频", "2025-01-01 12:00:00", 0, 0, 0),
        )
        conn.commit()
        conn.close()

        result = await platform.give_coin(1, (1, 1))
        assert result["success"] is True
        assert "coin_id" in result

    @pytest.mark.asyncio
    async def test_give_coin_exceeds_limit(self, platform):
        conn = sqlite3.connect(test_db_filepath)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (1, 1, "bili_user", 0, 0),
        )
        cursor.execute(
            "INSERT INTO post (post_id, user_id, content, created_at, "
            "num_likes, num_dislikes, num_shares) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, 1, "优质视频", "2025-01-01 12:00:00", 0, 0, 0),
        )
        conn.commit()
        conn.close()

        await platform.give_coin(1, (1, 2))
        result = await platform.give_coin(1, (1, 1))
        assert result["success"] is False
        assert "Max 2" in result["error"]

    @pytest.mark.asyncio
    async def test_give_coin_invalid_amount(self, platform):
        conn = sqlite3.connect(test_db_filepath)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (1, 1, "bili_user", 0, 0),
        )
        cursor.execute(
            "INSERT INTO post (post_id, user_id, content, created_at, "
            "num_likes, num_dislikes, num_shares) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, 1, "视频", "2025-01-01 12:00:00", 0, 0, 0),
        )
        conn.commit()
        conn.close()

        result = await platform.give_coin(1, (1, 5))
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_triple_tap(self, platform):
        conn = sqlite3.connect(test_db_filepath)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (1, 1, "bili_user1", 0, 0),
        )
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (2, 2, "bili_user2", 0, 0),
        )
        cursor.execute(
            "INSERT INTO post (post_id, user_id, content, created_at, "
            "num_likes, num_dislikes, num_shares) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, 2, "三连视频", "2025-01-01 12:00:00", 0, 0, 0),
        )
        conn.commit()
        conn.close()

        result = await platform.triple_tap(1, 1)
        assert result["success"] is True
        assert "like_id" in result
        assert "coin_id" in result
        assert "collection_id" in result

    @pytest.mark.asyncio
    async def test_triple_tap_nonexistent_post(self, platform):
        conn = sqlite3.connect(test_db_filepath)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (1, 1, "bili_user", 0, 0),
        )
        conn.commit()
        conn.close()

        result = await platform.triple_tap(1, 999)
        assert result["success"] is False

    def test_system_prompt(self, platform):
        prompt = platform.get_system_prompt(name="B站小白")
        assert "B站" in prompt or "Bilibili" in prompt
        assert "弹幕" in prompt


class TestBilibiliPrompts:
    def test_basic_prompt(self):
        prompt = get_bilibili_system_prompt(name="二次元少女")
        assert "B站" in prompt or "Bilibili" in prompt
        assert "弹幕" in prompt
        assert "三连" in prompt
        assert "投币" in prompt
        assert "二次元少女" in prompt
