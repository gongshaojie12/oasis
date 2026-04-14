"""Tests for the Weibo platform adapter."""

import os
import os.path as osp
import sqlite3

import pytest

from engine.platforms.weibo import (
    WeiboPlatform,
    _calculate_weibo_hot_score,
    rec_sys_weibo,
)
from engine.platforms.prompts.weibo import get_weibo_system_prompt

parent_folder = osp.dirname(osp.abspath(__file__))
test_db_filepath = osp.join(parent_folder, "test_weibo.db")


class TestWeiboHotScore:
    def test_positive_engagement(self):
        score = _calculate_weibo_hot_score(
            num_likes=100, num_dislikes=10, num_shares=50,
            num_comments=30, created_at_str="2025-01-01 12:00:00",
        )
        assert isinstance(score, float)

    def test_zero_engagement(self):
        score = _calculate_weibo_hot_score(
            num_likes=0, num_dislikes=0, num_shares=0,
            num_comments=0, created_at_str="2025-01-01 12:00:00",
        )
        assert isinstance(score, float)

    def test_shares_boost_score(self):
        score_no_shares = _calculate_weibo_hot_score(
            num_likes=10, num_dislikes=0, num_shares=0,
            num_comments=0, created_at_str="2025-01-01 12:00:00",
        )
        score_with_shares = _calculate_weibo_hot_score(
            num_likes=10, num_dislikes=0, num_shares=50,
            num_comments=0, created_at_str="2025-01-01 12:00:00",
        )
        assert score_with_shares > score_no_shares

    def test_comments_boost_score(self):
        score_no_comments = _calculate_weibo_hot_score(
            num_likes=10, num_dislikes=0, num_shares=0,
            num_comments=0, created_at_str="2025-01-01 12:00:00",
        )
        score_with_comments = _calculate_weibo_hot_score(
            num_likes=10, num_dislikes=0, num_shares=0,
            num_comments=100, created_at_str="2025-01-01 12:00:00",
        )
        assert score_with_comments > score_no_comments

    def test_newer_posts_score_higher(self):
        old = _calculate_weibo_hot_score(
            num_likes=10, num_dislikes=0, num_shares=0,
            num_comments=0, created_at_str="2020-01-01 12:00:00",
        )
        new = _calculate_weibo_hot_score(
            num_likes=10, num_dislikes=0, num_shares=0,
            num_comments=0, created_at_str="2025-06-01 12:00:00",
        )
        assert new > old

    def test_bad_datetime_format_does_not_crash(self):
        score = _calculate_weibo_hot_score(
            num_likes=5, num_dislikes=0, num_shares=0,
            num_comments=0, created_at_str="not-a-date",
        )
        assert isinstance(score, float)


class TestWeiboRecsys:
    def test_few_posts_returns_all(self):
        post_table = [
            {"post_id": 1, "num_likes": 5, "num_dislikes": 0,
             "num_shares": 1, "created_at": "2025-01-01 12:00:00"},
            {"post_id": 2, "num_likes": 3, "num_dislikes": 0,
             "num_shares": 0, "created_at": "2025-01-01 13:00:00"},
        ]
        rec_matrix = [[], [], []]
        result = rec_sys_weibo(post_table, rec_matrix, max_rec_post_len=10)
        assert len(result) == 3
        for row in result:
            assert set(row) == {1, 2}

    def test_top_k_selection(self):
        post_table = [
            {"post_id": i, "num_likes": i * 10, "num_dislikes": 0,
             "num_shares": i, "created_at": "2025-01-01 12:00:00"}
            for i in range(1, 20)
        ]
        rec_matrix = [[] for _ in range(5)]
        result = rec_sys_weibo(post_table, rec_matrix, max_rec_post_len=3)
        assert len(result) == 5
        for row in result:
            assert len(row) == 3

    def test_all_users_get_same_recs(self):
        post_table = [
            {"post_id": i, "num_likes": i, "num_dislikes": 0,
             "num_shares": 0, "created_at": "2025-01-01 12:00:00"}
            for i in range(1, 10)
        ]
        rec_matrix = [[] for _ in range(4)]
        result = rec_sys_weibo(post_table, rec_matrix, max_rec_post_len=3)
        assert result[0] == result[1] == result[2] == result[3]


class TestWeiboPlatform:
    @pytest.fixture
    def platform(self):
        if os.path.exists(test_db_filepath):
            os.remove(test_db_filepath)
        p = WeiboPlatform(db_path=test_db_filepath, recsys_type="reddit")
        yield p
        p.db_cursor.close()
        p.db.close()
        if os.path.exists(test_db_filepath):
            os.remove(test_db_filepath)

    def test_platform_name(self, platform):
        assert platform.PLATFORM_NAME == "weibo"

    def test_no_custom_actions(self, platform):
        assert platform.CUSTOM_ACTIONS == {}

    def test_system_prompt_contains_weibo(self, platform):
        prompt = platform.get_system_prompt(name="测试用户", bio="爱吃瓜")
        assert "微博" in prompt
        assert "测试用户" in prompt
        assert "爱吃瓜" in prompt

    @pytest.mark.asyncio
    async def test_create_post(self, platform):
        conn = sqlite3.connect(test_db_filepath)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (1, 1, "weibo_user", 0, 0),
        )
        conn.commit()
        conn.close()
        result = await platform.create_post(1, "今天天气真好 #日常#")
        assert result["success"] is True
        assert "post_id" in result


class TestWeiboPrompts:
    def test_basic_prompt(self):
        prompt = get_weibo_system_prompt(name="小明", bio="热爱生活")
        assert "微博" in prompt
        assert "小明" in prompt
        assert "热爱生活" in prompt
        assert "围观吃瓜" in prompt

    def test_prompt_with_profile(self):
        profile = {
            "other_info": {
                "user_profile": "科技博主，关注AI领域",
                "gender": "男",
                "age": 28,
                "mbti": "INTJ",
                "city": "北京",
            }
        }
        prompt = get_weibo_system_prompt(
            name="科技达人", bio="分享科技资讯", profile=profile,
        )
        assert "科技博主" in prompt
        assert "INTJ" in prompt
        assert "北京" in prompt

    def test_prompt_without_name(self):
        prompt = get_weibo_system_prompt()
        assert "微博" in prompt
