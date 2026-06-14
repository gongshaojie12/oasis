# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""EventBus + SimulationEvent (M3-11)."""
import asyncio

import pytest

from wanxiang.api.events import EventBus, SimulationEvent


def test_event_to_sse_format():
    ev = SimulationEvent(event="progress", data={"pct": 30})
    out = ev.to_sse()
    assert out.startswith("event: progress\n")
    assert 'data: {"pct": 30}\n\n' in out


def test_event_to_sse_chinese():
    ev = SimulationEvent(event="done", data={"msg": "完成"})
    out = ev.to_sse()
    assert "完成" in out  # not escaped to \uXXXX


def test_bus_publish_records_history():
    bus = EventBus()
    bus.publish("t1", "started", {"n": 100})
    h = bus.history("t1")
    assert len(h) == 1
    assert h[0].event == "started"
    assert h[0].data == {"n": 100}


def test_bus_publish_multiple():
    bus = EventBus()
    bus.publish("t1", "started", {})
    bus.publish("t1", "progress", {"pct": 50})
    bus.publish("t1", "done", {})
    assert len(bus.history("t1")) == 3
    events = [e.event for e in bus.history("t1")]
    assert events == ["started", "progress", "done"]


def test_bus_history_bounded():
    bus = EventBus(history_size=3)
    for i in range(10):
        bus.publish("t1", "progress", {"i": i})
    h = bus.history("t1")
    assert len(h) == 3
    # last 3 retained
    assert [e.data["i"] for e in h] == [7, 8, 9]


@pytest.mark.asyncio
async def test_bus_subscribe_yields_history_then_live():
    bus = EventBus()
    bus.publish("t1", "started", {"n": 10})
    bus.publish("t1", "progress", {"pct": 30})

    seen = []

    async def collector():
        async for ev in bus.subscribe("t1"):
            seen.append(ev.event)
            if ev.event == "done":
                break

    task = asyncio.create_task(collector())
    await asyncio.sleep(0.02)
    bus.publish("t1", "progress", {"pct": 70})
    bus.publish("t1", "done", {})
    bus.close("t1")
    await asyncio.wait_for(task, timeout=2.0)
    assert seen[0] == "started"
    assert "done" in seen


@pytest.mark.asyncio
async def test_bus_close_terminates_subscribers():
    bus = EventBus()
    bus.publish("t1", "started", {})
    seen = []

    async def consume():
        async for ev in bus.subscribe("t1"):
            seen.append(ev.event)

    task = asyncio.create_task(consume())
    await asyncio.sleep(0.02)
    bus.close("t1")
    await asyncio.wait_for(task, timeout=2.0)
    assert "started" in seen


@pytest.mark.asyncio
async def test_bus_subscribe_after_close_replays_history():
    bus = EventBus()
    bus.publish("t1", "started", {})
    bus.publish("t1", "done", {})
    bus.close("t1")
    seen = []
    async for ev in bus.subscribe("t1"):
        seen.append(ev.event)
    assert seen == ["started", "done"]


def test_bus_isolation_between_tasks():
    bus = EventBus()
    bus.publish("t1", "started", {})
    bus.publish("t2", "done", {})
    assert len(bus.history("t1")) == 1
    assert len(bus.history("t2")) == 1
    assert bus.history("t1")[0].event == "started"
    assert bus.history("t2")[0].event == "done"


def test_bus_history_empty_for_unknown_task():
    bus = EventBus()
    assert bus.history("nobody") == []


def test_event_timestamp_is_recent():
    import time
    before = time.time()
    ev = SimulationEvent(event="x", data={})
    after = time.time()
    assert before <= ev.timestamp <= after
