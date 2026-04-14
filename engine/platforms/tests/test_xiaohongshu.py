"""Tests for the Xiaohongshu platform adapter."""

import os
import os.path as osp
import sqlite3

import pytest

from engine.platforms.xiaohongshu import (
    XiaohongshuPlatform,
    rec_sys_xiaohongshu,
)
from engine.platforms.prompts.xiaohongshu import get_xiaohongshu_system_prompt

parent_folder = osp.dirname(osp.abspath(__file__))
test_db_filepath = osp.join(parent_folder, "test_xiaohongshu.db")


class TestXiaohongshuRecsys:
    def test_few_posts_returns_all(self):
        post_table = [
            {"post_id": 1, "num_likes": 5, "num_dislikes": 0,
             "num_shares": 1, "created_at": "2025-01-01 12:00:00"},
        ]
        rec_matrix = [[], []]
        result = rec_sys_xiaohongshu(post_table, rec_matrix, max_rec_post_len=5)
        assert len(result) == 2
        for row in result:
            assert 1 in row

    def test_top_k_selection(self):
        post_table = [
            {"post_id": i, "num_likes": i * 10, "num_dislikes": 0,
             "num_shares": 0, "created_at": "2025-01-01 12:00:00"}
            for i in range(1, 15)
        ]
        rec_matrix = [[] for _ in range(3)]
        result = rec_sys_xiaohongshu(
            post_table, rec_matrix, max_rec_post_len=5
        )
        assert len(result) == 3
        for row in result:
            assert len(row) == 5


class TestXiaohongshuPlatform:
    @pytest.fixture
    def platform(self):
        if os.path.exists(test_db_filepath):
            os.remove(test_db_filepath)
        p = XiaohongshuPlatform(
            db_path=test_db_filepath, recsys_type="random"
        )
        yield p
        p.db_cursor.close()
        p.db.close()
        if os.path.exists(test_db_filepath):
            os.remove(test_db_filepath)

    def test_platform_name(self, platform):
        assert platform.PLATFORM_NAME == "xiaohongshu"

    def test_custom_tables_created(self, platform):
        platform.db_cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='collection'"
        )
        assert platform.db_cursor.fetchone() is not None
        platform.db_cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='share'"
        )
        assert platform.db_cursor.fetchone() is not None

    @pytest.mark.asyncio
    async def test_collect_post(self, platform):
        conn = sqlite3.connect(test_db_filepath)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (1, 1, "xhs_user1", 0, 0),
        )
        cursor.execute(
            "INSERT INTO post (post_id, user_id, content, created_at, "
            "num_likes, num_dislikes, num_shares) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, 1, "种草分享", "2025-01-01 12:00:00", 0, 0, 0),
        )
        conn.commit()
        conn.close()
        result = await platform.collect_post(1, 1)
        assert result["success"] is True
        assert "collection_id" in result

    @pytest.mark.asyncio
    async def test_collect_post_duplicate(self, platform):
        conn = sqlite3.connect(test_db_filepath)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (1, 1, "xhs_user1", 0, 0),
        )
        cursor.execute(
            "INSERT INTO post (post_id, user_id, content, created_at, "
            "num_likes, num_dislikes, num_shares) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, 1, "种草分享", "2025-01-01 12:00:00", 0, 0, 0),
        )
        conn.commit()
        conn.close()
        await platform.collect_post(1, 1)
        result = await platform.collect_post(1, 1)
        assert result["success"] is False
        assert "already exists" in result["error"]

    @pytest.mark.asyncio
    async def test_share_post(self, platform):
        conn = sqlite3.connect(test_db_filepath)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (1, 1, "xhs_user1", 0, 0),
        )
        cursor.execute(
            "INSERT INTO post (post_id, user_id, content, created_at, "
            "num_likes, num_dislikes, num_shares) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, 1, "好物推荐", "2025-01-01 12:00:00", 0, 0, 0),
        )
        conn.commit()
        conn.close()
        result = await platform.share_post(1, 1)
        assert result["success"] is True
        assert "share_id" in result

    @pytest.mark.asyncio
    async def test_share_nonexistent_post(self, platform):
        conn = sqlite3.connect(test_db_filepath)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (1, 1, "xhs_user1", 0, 0),
        )
        conn.commit()
        conn.close()
        result = await platform.share_post(1, 999)
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_system_prompt(self, platform):
        prompt = platform.get_system_prompt(
            name="小红薯", bio="分享美好生活"
        )
        assert "小红书" in prompt
        assert "种草" in prompt
        assert "小红薯" in prompt


class TestXiaohongshuPrompts:
    def test_basic_prompt(self):
        prompt = get_xiaohongshu_system_prompt(name="美妆达人")
        assert "小红书" in prompt
        assert "种草" in prompt
        assert "收藏" in prompt
        assert "美妆达人" in prompt

    def test_prompt_with_emoji_mention(self):
        prompt = get_xiaohongshu_system_prompt()
        assert "emoji" in prompt
