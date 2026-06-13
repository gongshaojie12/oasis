# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
from datetime import datetime, timedelta

from engine.clock import Clock


def test_clock_get_time_step_starts_at_zero():
    c = Clock(k=60)
    assert c.get_time_step() == "0"
    c.time_step += 1
    assert c.get_time_step() == "1"


def test_clock_time_transfer_scales_elapsed():
    c = Clock(k=2)
    start = datetime(2026, 1, 1, 0, 0, 0)
    now = c.real_start_time + timedelta(seconds=10)
    result = c.time_transfer(now, start)
    assert result == start + timedelta(seconds=20)


def test_clock_default_k_is_one():
    c = Clock()
    assert c.k == 1
