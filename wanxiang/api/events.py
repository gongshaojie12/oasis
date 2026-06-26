# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""SSE 事件总线 (M3-11 + Stage 1+2).

两种实现：
- ``InMemoryEventBus`` — 进程内 asyncio.Queue + 环形 history buffer。
  单机模式默认使用，零外部依赖。
- ``RedisEventBus`` — 跨进程 Redis Pub/Sub + LIST history。
  Celery worker 模式使用，多进程/多机器共享事件流。

设计原则：
- 即使没有订阅者，事件也不阻塞写入（in-memory: 队列容量大，溢出时丢最早；
  redis: LIST + LTRIM 限长）。
- 维护 per-task history，让"迟到"订阅者能补看到 task 已经发出的事件
  （subscribe 先重放 history，再切到 live channel/queue）。
- 任务结束时往 queue/channel 推一个结束哨兵，订阅端读到立即关闭流。

向后兼容：``EventBus`` 保留为 ``InMemoryEventBus`` 别名，老代码 import 不破坏。
环境切换：``get_event_bus()`` 根据 ``WANXIANG_EVENT_BUS`` 选择实现。
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from collections import deque
from dataclasses import dataclass, field
from typing import AsyncIterator


@dataclass
class SimulationEvent:
    """Single event payload."""
    event: str          # "started" | "progress" | "done" | "error" | ...
    data: dict
    timestamp: float = field(default_factory=time.time)

    def to_sse(self) -> str:
        """Serialize as a single SSE message block.

        SSE wire format:
          event: <name>\\n
          data: <json>\\n
          \\n
        """
        payload = json.dumps(self.data, ensure_ascii=False)
        return f"event: {self.event}\ndata: {payload}\n\n"


class InMemoryEventBus:
    """Per-task event channels + per-task event ring buffer for replay.

    维护:
    - `_queues[task_id]`: live `asyncio.Queue`，订阅者从这里阻塞读
    - `_history[task_id]`: 有界 `deque`（默认 1024 条），让迟到订阅者重放
    - `_closed`: 哪些 task 已经收到 close()

    history 是 best-effort：满了就 trim 最早的，永远不阻塞 producer。
    """

    def __init__(self, history_size: int = 1024):
        self._queues: dict[str, asyncio.Queue] = {}
        self._history: dict[str, deque] = {}
        self._closed: set[str] = set()
        self._history_size = history_size

    def _ensure(self, task_id: str) -> asyncio.Queue:
        if task_id not in self._queues:
            self._queues[task_id] = asyncio.Queue(maxsize=4096)
            self._history[task_id] = deque(maxlen=self._history_size)
        return self._queues[task_id]

    def publish(self, task_id: str, event: str, data: dict) -> None:
        ev = SimulationEvent(event=event, data=data)
        q = self._ensure(task_id)
        self._history[task_id].append(ev)
        try:
            q.put_nowait(ev)
        except asyncio.QueueFull:
            # 满了：把最早一条扔掉再塞
            try:
                q.get_nowait()
            except asyncio.QueueEmpty:
                pass
            try:
                q.put_nowait(ev)
            except asyncio.QueueFull:
                pass

    def close(self, task_id: str) -> None:
        """Signal end-of-stream by enqueuing a None sentinel."""
        self._closed.add(task_id)
        q = self._ensure(task_id)
        try:
            q.put_nowait(None)
        except asyncio.QueueFull:
            # 把最早一条扔掉再塞哨兵，确保 subscribe 一定能收到结束信号
            try:
                q.get_nowait()
            except asyncio.QueueEmpty:
                pass
            try:
                q.put_nowait(None)
            except asyncio.QueueFull:
                pass

    async def subscribe(self, task_id: str) -> AsyncIterator[SimulationEvent]:
        """Yield events for task_id.

        先把已经在 history 里的 buffered 事件全部 yield 出去（重放），
        然后:
        - 如果 task 已经 close → 直接结束 iteration
        - 否则切到 live queue，阻塞读直到收到 None 哨兵

        注意 history 重放与 live queue 之间存在窗口期：subscriber 重放完
        history 后，live queue 可能还残留着相同的事件副本——但 dedupe
        过于复杂且最终被 close() 哨兵兜底，调用方应该容忍重复事件。
        实践上 history 与 queue 是同步追加的，重放阶段不消费 queue，所以
        正常情况只会出现 "history 重放 N 条 + queue 中残留 N 条同样的事件"。
        这里采用 best-effort：subscribe 时先 snapshot history 长度，跳过
        queue 中前 N 条事件来避免重复。
        """
        history_snapshot = list(self._history.get(task_id, []))
        for ev in history_snapshot:
            yield ev
        if task_id in self._closed:
            return
        q = self._ensure(task_id)
        skip = len(history_snapshot)
        while True:
            ev = await q.get()
            if ev is None:
                return
            if skip > 0:
                skip -= 1
                continue
            yield ev

    def history(self, task_id: str) -> list[SimulationEvent]:
        """Snapshot of buffered events (for tests + replay introspection)."""
        return list(self._history.get(task_id, []))


# Backward-compat: keep ``EventBus`` importable as the in-memory implementation.
EventBus = InMemoryEventBus


# ---------------------------------------------------------------------------
# Redis-backed event bus (Stage 1+2 distributed mode)
# ---------------------------------------------------------------------------

_CLOSE_SENTINEL = "__CLOSE__"


class RedisEventBus:
    """Cross-process event bus using Redis LIST (history) + Pub/Sub (live).

    Wire conventions:
    - History key: ``wanxiang:events:{task_id}`` (Redis LIST, capped by LTRIM)
    - Live channel: same key, used as a Pub/Sub channel
    - Close signal: a final ``{"event":"__CLOSE__", ...}`` message published
      to the channel **and** appended to the LIST; ``history()`` strips it.

    All event payloads are JSON-encoded (UTF-8, no ASCII escaping).
    """

    def __init__(self, redis_url: str, *, history_size: int = 1024,
                 ttl_seconds: int = 7 * 24 * 3600):
        import redis  # lazy import — only when distributed mode is enabled
        self._r = redis.Redis.from_url(redis_url, decode_responses=True)
        self._history_size = history_size
        self._ttl = ttl_seconds

    @staticmethod
    def _key(task_id: str) -> str:
        return f"wanxiang:events:{task_id}"

    def publish(self, task_id: str, event: str, data: dict) -> None:
        ev_dict = {"event": event, "data": data, "timestamp": time.time()}
        s = json.dumps(ev_dict, ensure_ascii=False)
        key = self._key(task_id)
        pipe = self._r.pipeline()
        pipe.rpush(key, s)
        # LTRIM keeps the last `history_size` entries.
        pipe.ltrim(key, -self._history_size, -1)
        pipe.expire(key, self._ttl)
        pipe.publish(key, s)
        pipe.execute()
        # publish() must explicitly return None (tests rely on it).
        return None

    def close(self, task_id: str) -> None:
        self.publish(task_id, _CLOSE_SENTINEL, {"task_id": task_id})

    def history(self, task_id: str) -> list[SimulationEvent]:
        raw = self._r.lrange(self._key(task_id), 0, -1)
        out: list[SimulationEvent] = []
        for s in raw:
            try:
                d = json.loads(s)
            except (TypeError, ValueError):
                continue
            if d.get("event") == _CLOSE_SENTINEL:
                continue
            out.append(SimulationEvent(
                event=d["event"], data=d.get("data") or {},
                timestamp=d.get("timestamp") or time.time()))
        return out

    async def subscribe(self, task_id: str) -> AsyncIterator[SimulationEvent]:
        """按索引轮询 history LIST,逐条产出直到 close 哨兵。

        历史教训:原实现先 snapshot history 再 subscribe pub/sub,但 pub/sub
        是 fire-and-forget —— 在 snapshot 与 subscribe 之间 publish 的事件会
        永久丢失。快速模拟(并发完成)时大量 progress/done 因此丢失,SSE 只
        收到前几条就断流。

        改为对 history LIST 做 index 轮询:RPUSH 原子有序、LIST 保留全部事件
        (含 __CLOSE__ 哨兵且不被 LTRIM 在 ≤history_size 时丢弃),故无竞态。
        延迟 = 轮询间隔(0.12s),对实时面板足够。
        """
        key = self._key(task_id)
        idx = 0  # 下一个要读的 LIST 下标
        while True:
            raw_items = self._r.lrange(key, idx, -1)
            if raw_items:
                idx += len(raw_items)
                for s in raw_items:
                    try:
                        d = json.loads(s)
                    except (TypeError, ValueError):
                        continue
                    if d.get("event") == _CLOSE_SENTINEL:
                        return
                    yield SimulationEvent(
                        event=d["event"], data=d.get("data") or {},
                        timestamp=d.get("timestamp") or time.time())
            else:
                await asyncio.sleep(0.12)


def get_event_bus():
    """Factory: pick implementation based on ``WANXIANG_EVENT_BUS``.

    - ``"memory"`` (default) → :class:`InMemoryEventBus`
    - ``"redis"`` → :class:`RedisEventBus` configured by
      ``WANXIANG_REDIS_URL`` (default ``redis://localhost:6379/2``).
    """
    mode = os.environ.get("WANXIANG_EVENT_BUS", "memory").lower()
    if mode == "redis":
        url = os.environ.get("WANXIANG_REDIS_URL",
                             "redis://localhost:6379/2")
        return RedisEventBus(url)
    return InMemoryEventBus()
