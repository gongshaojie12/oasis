from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger("engine.websocket.commands")


class CommandQueue:
    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._paused = False
        self._speed = 1.0
        self._injected_events: list[dict[str, Any]] = []

    @property
    def is_paused(self) -> bool:
        return self._paused

    @property
    def speed(self) -> float:
        return self._speed

    def get_injected_events(self) -> list[dict[str, Any]]:
        events = self._injected_events.copy()
        self._injected_events.clear()
        return events

    async def put(self, command: str, payload: dict[str, Any] | None = None):
        await self._queue.put((command, payload or {}))

    async def process_pending(self):
        while not self._queue.empty():
            try:
                command, payload = self._queue.get_nowait()
                self._handle(command, payload)
            except asyncio.QueueEmpty:
                break

    def _handle(self, command: str, payload: dict[str, Any]):
        if command == "command:pause":
            self._paused = True
            logger.info("Simulation paused")
        elif command == "command:resume":
            self._paused = False
            logger.info("Simulation resumed")
        elif command == "command:speed":
            self._speed = payload.get("speed", 1.0)
            logger.info("Speed changed to %s", self._speed)
        elif command == "command:inject":
            self._injected_events.append(payload)
            logger.info("Event injected: %s", payload.get("content", "")[:50])
        elif command == "command:step":
            self._paused = False
            logger.info("Single step requested")

    async def wait_while_paused(self):
        while self._paused:
            await asyncio.sleep(0.2)
            await self.process_pending()
