# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""SSE 事件总线 (M3-11).

每个异步 task_id 对应一个 asyncio.Queue。任务执行时往 queue 里放事件，
SSE 路由订阅 queue 并以 text/event-stream 推送。

设计原则：
- 即使没有订阅者，事件也不阻塞写入（队列容量大，溢出时丢最早）。
- 多个订阅者共享同一 queue 是错的（先到先得）；多订阅需扇出。MVP 单订阅即可。
- 任务结束时往 queue 推一个 None 哨兵，订阅端读到立即关闭流。
- 维护 per-task 的环形 history buffer，让"迟到"订阅者能补看到 task 已经发出
  的事件（subscribe 先把 history 全部 yield 出去，再切到 live queue）。
"""
from __future__ import annotations

import asyncio
import json
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


class EventBus:
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
