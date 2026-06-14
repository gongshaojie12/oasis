# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""RedisEventBus tests using fakeredis (no real Redis required)."""
from __future__ import annotations

import pytest


@pytest.fixture
def bus(monkeypatch):
    import fakeredis
    import redis
    fake = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(
        redis.Redis, "from_url",
        classmethod(lambda cls, *a, **kw: fake))
    from wanxiang.api.events import RedisEventBus
    return RedisEventBus("redis://fake")


def test_publish_and_history(bus):
    bus.publish("t1", "started", {"n": 10})
    bus.publish("t1", "done", {"n_valid": 8})
    h = bus.history("t1")
    assert len(h) == 2
    assert h[0].event == "started"
    assert h[1].event == "done"
    assert h[0].data == {"n": 10}
    assert h[1].data == {"n_valid": 8}


def test_publish_tenant_isolation(bus):
    bus.publish("t1", "started", {})
    bus.publish("t2", "done", {})
    h1 = bus.history("t1")
    h2 = bus.history("t2")
    assert len(h1) == 1 and h1[0].event == "started"
    assert len(h2) == 1 and h2[0].event == "done"


def test_history_bounded(monkeypatch):
    import fakeredis
    import redis
    fake = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(
        redis.Redis, "from_url",
        classmethod(lambda cls, *a, **kw: fake))
    from wanxiang.api.events import RedisEventBus
    bus = RedisEventBus("redis://fake", history_size=3)
    for i in range(10):
        bus.publish("t1", "progress", {"i": i})
    h = bus.history("t1")
    assert len(h) == 3
    assert [e.data["i"] for e in h] == [7, 8, 9]


def test_close_writes_sentinel_but_history_excludes_it(bus):
    bus.publish("t1", "started", {})
    bus.close("t1")
    h = bus.history("t1")
    # close sentinel should never appear in history
    assert all(e.event != "__CLOSE__" for e in h)
    assert len(h) == 1
    assert h[0].event == "started"


def test_chinese_data_preserved(bus):
    bus.publish("t1", "done", {"msg": "完成"})
    h = bus.history("t1")
    assert h[0].data["msg"] == "完成"


def test_publish_returns_none(bus):
    assert bus.publish("t1", "x", {}) is None


def test_history_empty_for_unknown_task(bus):
    assert bus.history("unknown-task-id") == []
