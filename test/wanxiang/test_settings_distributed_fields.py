# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""ServerSettings: distributed-mode fields (task_queue / event_bus / redis)."""
from __future__ import annotations


def test_task_queue_default_asyncio(monkeypatch):
    monkeypatch.delenv("WANXIANG_TASK_QUEUE", raising=False)
    from wanxiang.api.server import ServerSettings
    s = ServerSettings()
    assert s.task_queue == "asyncio"


def test_event_bus_default_memory(monkeypatch):
    monkeypatch.delenv("WANXIANG_EVENT_BUS", raising=False)
    from wanxiang.api.server import ServerSettings
    s = ServerSettings()
    assert s.event_bus == "memory"


def test_redis_url_default(monkeypatch):
    monkeypatch.delenv("WANXIANG_REDIS_URL", raising=False)
    from wanxiang.api.server import ServerSettings
    s = ServerSettings()
    assert s.redis_url.startswith("redis://")


def test_celery_broker_and_backend_defaults(monkeypatch):
    monkeypatch.delenv("WANXIANG_CELERY_BROKER", raising=False)
    monkeypatch.delenv("WANXIANG_CELERY_BACKEND", raising=False)
    from wanxiang.api.server import ServerSettings
    s = ServerSettings()
    assert s.celery_broker.startswith("redis://")
    assert s.celery_backend.startswith("redis://")


def test_task_queue_env_override(monkeypatch):
    monkeypatch.setenv("WANXIANG_TASK_QUEUE", "celery")
    from wanxiang.api.server import ServerSettings
    s = ServerSettings()
    assert s.task_queue == "celery"
