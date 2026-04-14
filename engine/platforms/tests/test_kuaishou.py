"""Tests for the Kuaishou platform adapter."""

import os
import os.path as osp
import sqlite3

import pytest

from engine.platforms.kuaishou import (
    KuaishouPlatform,
    rec_sys_kuaishou,
)
from engine.platforms.prompts.kuaishou import get_kuaishou_system_prompt

parent_folder = osp.dirname(osp.abspath(__file__))
test_db_filepath = osp.join(parent_folder, "test_kuaishou.db")


class TestKuaishouRecsys:
    def test_few_posts_returns_all(self):
        user_table = [{"user_id": 0}, {"user_id": 1}]
        post_table = [
            {"post_id": 1, "user_id": 0, "num_likes": 5, "num_shares": 1},
        ]
        rec_matrix = [[], []]
        result = rec_sys_kuaishou(
            user_table, post_table, rec_matrix, max_rec_post_len=5
        )
        assert len(result) == 2
        for row in result:
            assert 1 in row

    def test_follow_weighting(self):
        user_table = [{"user_id": 0}, {"user_id": 1}, {"user_id": 2}]
        post_table = [
            {"post_id": i, "user_id": i % 3, "num_likes": 1, "num_shares": 0}
            for i in range(1, 10)
        ]
        rec_matrix = [[] for _ in range(3)]
        result = rec_sys_kuaishou(
            user_table, post_table, rec_matrix, max_rec_post_len=3
        )
        assert len(result) == 3
        for row in result:
            assert len(row) == 3


class TestKuaishouPlatform:
    @pytest.fixture
    def platform(self):
        if os.path.exists(test_db_filepath):
            os.remove(test_db_filepath)
        p = KuaishouPlatform(db_path=test_db_filepath, recsys_type="random")
        yield p
        p.db_cursor.close()
        p.db.close()
        if os.path.exists(test_db_filepath):
            os.remove(test_db_filepath)

    def test_platform_name(self, platform):
        assert platform.PLATFORM_NAME == "kuaishou"

    def test_custom_tables_created(self, platform):
        platform.db_cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='gift'"
        )
        assert platform.db_cursor.fetchone() is not None
        platform.db_cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='shuoshuo'"
        )
        assert platform.db_cursor.fetchone() is not None

    @pytest.mark.asyncio
    async def test_send_gift(self, platform):
        conn = sqlite3.connect(test_db_filepath)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (1, 1, "ks_user1", 0, 0),
        )
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (2, 2, "ks_user2", 0, 0),
        )
        cursor.execute(
            "INSERT INTO post (post_id, user_id, content, created_at, "
            "num_likes, num_dislikes, num_shares) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, 2, "老铁双击666", "2025-01-01 12:00:00", 0, 0, 0),
        )
        conn.commit()
        conn.close()

        result = await platform.send_gift(1, (1, 10))
        assert result["success"] is True
        assert "gift_id" in result
        assert result["receiver_id"] == 2

    @pytest.mark.asyncio
    async def test_send_gift_to_self_fails(self, platform):
        conn = sqlite3.connect(test_db_filepath)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (1, 1, "ks_user1", 0, 0),
        )
        cursor.execute(
            "INSERT INTO post (post_id, user_id, content, created_at, "
            "num_likes, num_dislikes, num_shares) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, 1, "自己的内容", "2025-01-01 12:00:00", 0, 0, 0),
        )
        conn.commit()
        conn.close()

        result = await platform.send_gift(1, (1, 5))
        assert result["success"] is False
        assert "yourself" in result["error"]

    @pytest.mark.asyncio
    async def test_send_gift_nonexistent_post(self, platform):
        conn = sqlite3.connect(test_db_filepath)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (1, 1, "ks_user1", 0, 0),
        )
        conn.commit()
        conn.close()

        result = await platform.send_gift(1, (999, 5))
        assert result["success"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_post_shuoshuo(self, platform):
        conn = sqlite3.connect(test_db_filepath)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (1, 1, "ks_user1", 0, 0),
        )
        conn.commit()
        conn.close()

        result = await platform.post_shuoshuo(1, "今天心情不错，老铁们！")
        assert result["success"] is True
        assert "shuoshuo_id" in result

    def test_system_prompt(self, platform):
        prompt = platform.get_system_prompt(name="老铁小王")
        assert "快手" in prompt
        assert "老铁" in prompt


class TestKuaishouPrompts:
    def test_basic_prompt(self):
        prompt = get_kuaishou_system_prompt(name="铁粉小李")
        assert "快手" in prompt
        assert "老铁" in prompt
        assert "铁粉小李" in prompt
        assert "下沉市场" in prompt
