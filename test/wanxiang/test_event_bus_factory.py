# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""get_event_bus() factory + backward-compat aliasing (Stage 1+2)."""
from __future__ import annotations

import pytest


def test_get_event_bus_default_is_in_memory(monkeypatch):
    monkeypatch.delenv("WANXIANG_EVENT_BUS", raising=False)
    from wanxiang.api.events import get_event_bus, InMemoryEventBus
    bus = get_event_bus()
    assert isinstance(bus, InMemoryEventBus)


def test_get_event_bus_memory_explicit(monkeypatch):
    monkeypatch.setenv("WANXIANG_EVENT_BUS", "memory")
    from wanxiang.api.events import get_event_bus, InMemoryEventBus
    bus = get_event_bus()
    assert isinstance(bus, InMemoryEventBus)


def test_get_event_bus_redis(monkeypatch):
    import fakeredis
    import redis
    monkeypatch.setattr(
        redis.Redis, "from_url",
        classmethod(lambda cls, *a, **kw:
                    fakeredis.FakeRedis(decode_responses=True)))
    monkeypatch.setenv("WANXIANG_EVENT_BUS", "redis")
    from wanxiang.api.events import get_event_bus, RedisEventBus
    bus = get_event_bus()
    assert isinstance(bus, RedisEventBus)


def test_event_bus_backward_compat_alias():
    """Old `from wanxiang.api.events import EventBus` must still work."""
    from wanxiang.api.events import EventBus, InMemoryEventBus
    # EventBus stays importable; should be the in-memory class (or its alias).
    bus = EventBus()
    assert isinstance(bus, InMemoryEventBus)


def test_event_bus_alias_same_runtime_class():
    """The aliased EventBus must produce instances usable by old code paths."""
    from wanxiang.api.events import EventBus
    bus = EventBus()
    bus.publish("t1", "started", {"n": 1})
    assert len(bus.history("t1")) == 1
