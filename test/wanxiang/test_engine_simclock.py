# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""验证 engine.simclock.compute_current_time —— 抽取自 platform.py 中
重复 21 次的 current_time 计算块。"""
from datetime import datetime, timedelta

from engine.clock import Clock
from engine.simclock import compute_current_time


class _RecsysReddit:
    value = "reddit"


def test_reddit_uses_time_transfer():
    # reddit 分支：返回基于 start_time + k*elapsed 的 datetime
    clock = Clock(k=2)
    start = datetime(2026, 1, 1, 0, 0, 0)
    now = clock.real_start_time + timedelta(seconds=5)
    result = compute_current_time("reddit", clock, start, now=now)
    assert result == start + timedelta(seconds=10)


def test_twitter_uses_time_step():
    # 非 reddit 分支：返回离散 time_step 字符串
    clock = Clock(k=60)
    clock.time_step = 3
    result = compute_current_time("twitter", clock, datetime(2026, 1, 1))
    assert result == "3"


def test_accepts_enum_like_recsys_type():
    # 兼容传入带 .value == "reddit" 的枚举对象
    clock = Clock(k=1)
    start = datetime(2026, 1, 1)
    now = clock.real_start_time + timedelta(seconds=7)
    result = compute_current_time(_RecsysReddit(), clock, start, now=now)
    assert result == start + timedelta(seconds=7)
