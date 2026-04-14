"""Tests for the WeChat Video platform adapter."""

import os
import os.path as osp
import sqlite3

import pytest

from engine.platforms.wechat_video import (
    WeChatVideoPlatform,
    rec_sys_wechat_video,
)
from engine.platforms.prompts.wechat_video import (
    get_wechat_video_system_prompt,
)

parent_folder = osp.dirname(osp.abspath(__file__))
test_db_filepath = osp.join(parent_folder, "test_wechat_video.db")


class TestWeChatVideoRecsys:
    def test_few_posts_returns_all(self):
        user_table = [{"user_id": 0}]
        post_table = [
            {"post_id": 1, "user_id": 0, "num_likes": 5, "num_shares": 1},
        ]
        rec_matrix = [[]]
        result = rec_sys_wechat_video(
            user_table, post_table, rec_matrix, max_rec_post_len=5
        )
        assert len(result) == 1
        assert 1 in result[0]

    def test_top_k_selection(self):
        user_table = [{"user_id": i} for i in range(3)]
        post_table = [
            {"post_id": i, "user_id": i % 3, "num_likes": i * 2,
             "num_shares": 0}
            for i in range(1, 15)
        ]
        rec_matrix = [[] for _ in range(3)]
        result = rec_sys_wechat_video(
            user_table, post_table, rec_matrix, max_rec_post_len=3
        )
        assert len(result) == 3
        for row in result:
            assert len(row) == 3


class TestWeChatVideoPlatform:
    @pytest.fixture
    def platform(self):
        if os.path.exists(test_db_filepath):
            os.remove(test_db_filepath)
        p = WeChatVideoPlatform(
            db_path=test_db_filepath, recsys_type="random"
        )
        yield p
        p.db_cursor.close()
        p.db.close()
        if os.path.exists(test_db_filepath):
            os.remove(test_db_filepath)

    def test_platform_name(self, platform):
        assert platform.PLATFORM_NAME == "wechat_video"

    def test_friend_share_table_created(self, platform):
        platform.db_cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='friend_share'"
        )
        assert platform.db_cursor.fetchone() is not None

    @pytest.mark.asyncio
    async def test_share_to_friends(self, platform):
        conn = sqlite3.connect(test_db_filepath)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (1, 1, "wx_user1", 0, 0),
        )
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (2, 2, "wx_user2", 0, 0),
        )
        cursor.execute(
            "INSERT INTO post (post_id, user_id, content, created_at, "
            "num_likes, num_dislikes, num_shares) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, 1, "正能量视频", "2025-01-01 12:00:00", 0, 0, 0),
        )
        conn.commit()
        conn.close()

        result = await platform.share_to_friends(
            1, (1, 2, "这个视频很不错，推荐给你看看")
        )
        assert result["success"] is True
        assert "share_id" in result
        assert result["target_user_id"] == 2

    @pytest.mark.asyncio
    async def test_share_to_self_fails(self, platform):
        conn = sqlite3.connect(test_db_filepath)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (1, 1, "wx_user1", 0, 0),
        )
        cursor.execute(
            "INSERT INTO post (post_id, user_id, content, created_at, "
            "num_likes, num_dislikes, num_shares) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, 1, "视频", "2025-01-01 12:00:00", 0, 0, 0),
        )
        conn.commit()
        conn.close()

        result = await platform.share_to_friends(1, (1, 1, "分享"))
        assert result["success"] is False
        assert "yourself" in result["error"]

    @pytest.mark.asyncio
    async def test_share_nonexistent_post(self, platform):
        conn = sqlite3.connect(test_db_filepath)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (1, 1, "wx_user1", 0, 0),
        )
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (2, 2, "wx_user2", 0, 0),
        )
        conn.commit()
        conn.close()

        result = await platform.share_to_friends(1, (999, 2, "看看"))
        assert result["success"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_share_to_nonexistent_user(self, platform):
        conn = sqlite3.connect(test_db_filepath)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (1, 1, "wx_user1", 0, 0),
        )
        cursor.execute(
            "INSERT INTO post (post_id, user_id, content, created_at, "
            "num_likes, num_dislikes, num_shares) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, 1, "视频", "2025-01-01 12:00:00", 0, 0, 0),
        )
        conn.commit()
        conn.close()

        result = await platform.share_to_friends(1, (1, 999, "看看"))
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_system_prompt(self, platform):
        prompt = platform.get_system_prompt(name="李阿姨")
        assert "视频号" in prompt
        assert "正能量" in prompt


class TestWeChatVideoPrompts:
    def test_basic_prompt(self):
        prompt = get_wechat_video_system_prompt(name="王叔叔")
        assert "视频号" in prompt
        assert "正能量" in prompt
        assert "分享" in prompt
        assert "朋友" in prompt
        assert "王叔叔" in prompt

    def test_prompt_with_profile(self):
        profile = {
            "other_info": {
                "user_profile": "退休教师，热爱生活",
                "gender": "女",
                "age": 55,
                "city": "杭州",
            }
        }
        prompt = get_wechat_video_system_prompt(
            name="张老师", profile=profile,
        )
        assert "退休教师" in prompt
        assert "杭州" in prompt
