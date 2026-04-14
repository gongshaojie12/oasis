"""Tests for the Douyin platform adapter."""

import os
import os.path as osp
import sqlite3

import pytest

from engine.platforms.douyin import (
    DouyinPlatform,
    _calculate_engagement_rate,
    rec_sys_douyin,
)
from engine.platforms.prompts.douyin import get_douyin_system_prompt

parent_folder = osp.dirname(osp.abspath(__file__))
test_db_filepath = osp.join(parent_folder, "test_douyin.db")


class TestEngagementRate:
    def test_zero_interactions(self):
        post = {"num_likes": 0, "num_dislikes": 0, "num_shares": 0}
        assert _calculate_engagement_rate(post) == 0.0

    def test_all_positive(self):
        post = {"num_likes": 10, "num_dislikes": 0, "num_shares": 5}
        rate = _calculate_engagement_rate(post)
        assert rate == 1.0

    def test_mixed_engagement(self):
        post = {"num_likes": 7, "num_dislikes": 3, "num_shares": 0}
        rate = _calculate_engagement_rate(post)
        assert 0.0 < rate < 1.0
        assert abs(rate - 0.7) < 0.01


class TestDouyinRecsys:
    def test_few_posts_returns_all(self):
        post_table = [
            {"post_id": 1, "num_likes": 5, "num_dislikes": 0, "num_shares": 0},
        ]
        rec_matrix = [[], [], []]
        result = rec_sys_douyin(post_table, rec_matrix, max_rec_post_len=5)
        assert len(result) == 3
        for row in result:
            assert 1 in row

    def test_tiered_distribution(self):
        post_table = [
            {"post_id": 1, "num_likes": 100, "num_dislikes": 0,
             "num_shares": 50},
            {"post_id": 2, "num_likes": 5, "num_dislikes": 3,
             "num_shares": 2},
            {"post_id": 3, "num_likes": 0, "num_dislikes": 0,
             "num_shares": 0},
        ]
        rec_matrix = [[] for _ in range(10)]
        result = rec_sys_douyin(
            post_table, rec_matrix, max_rec_post_len=2,
            tier1_size=3, tier2_size=6,
        )
        assert len(result) == 10
        post1_count = sum(1 for row in result if 1 in row)
        assert post1_count == 10

    def test_output_length_capped(self):
        post_table = [
            {"post_id": i, "num_likes": i, "num_dislikes": 0,
             "num_shares": 0}
            for i in range(1, 20)
        ]
        rec_matrix = [[] for _ in range(5)]
        result = rec_sys_douyin(post_table, rec_matrix, max_rec_post_len=3)
        for row in result:
            assert len(row) <= 3


class TestDouyinPlatform:
    @pytest.fixture
    def platform(self):
        if os.path.exists(test_db_filepath):
            os.remove(test_db_filepath)
        p = DouyinPlatform(db_path=test_db_filepath, recsys_type="random")
        yield p
        p.db_cursor.close()
        p.db.close()
        if os.path.exists(test_db_filepath):
            os.remove(test_db_filepath)

    def test_platform_name(self, platform):
        assert platform.PLATFORM_NAME == "douyin"

    def test_collection_table_created(self, platform):
        platform.db_cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='collection'"
        )
        assert platform.db_cursor.fetchone() is not None

    @pytest.mark.asyncio
    async def test_collect_post(self, platform):
        conn = sqlite3.connect(test_db_filepath)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (1, 1, "douyin_user", 0, 0),
        )
        cursor.execute(
            "INSERT INTO post (post_id, user_id, content, created_at, "
            "num_likes, num_dislikes, num_shares) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, 1, "抖音热门视频", "2025-01-01 12:00:00", 0, 0, 0),
        )
        conn.commit()
        conn.close()

        result = await platform.collect_post(1, 1)
        assert result["success"] is True

        result2 = await platform.collect_post(1, 1)
        assert result2["success"] is False

    def test_system_prompt(self, platform):
        prompt = platform.get_system_prompt(name="抖音达人")
        assert "抖音" in prompt
        assert "短视频" in prompt


class TestDouyinPrompts:
    def test_basic_prompt(self):
        prompt = get_douyin_system_prompt(name="创作者小王")
        assert "抖音" in prompt
        assert "创作者小王" in prompt
        assert "短视频" in prompt
