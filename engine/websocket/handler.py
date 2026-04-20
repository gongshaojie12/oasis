from __future__ import annotations

import json
import logging

from fastapi import WebSocket, WebSocketDisconnect

from engine.websocket.protocol import WSMessage
from engine.websocket.commands import CommandQueue

logger = logging.getLogger("engine.websocket.handler")


class SimulationWSManager:
    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = {}
        self._command_queues: dict[str, CommandQueue] = {}

    def get_command_queue(self, task_id: str) -> CommandQueue:
        if task_id not in self._command_queues:
            self._command_queues[task_id] = CommandQueue()
        return self._command_queues[task_id]

    async def connect(self, task_id: str, ws: WebSocket):
        await ws.accept()
        if task_id not in self._connections:
            self._connections[task_id] = []
        self._connections[task_id].append(ws)
        logger.info("WS client connected for task %s", task_id)

    def disconnect(self, task_id: str, ws: WebSocket):
        if task_id in self._connections:
            self._connections[task_id] = [c for c in self._connections[task_id] if c != ws]
            if not self._connections[task_id]:
                del self._connections[task_id]
        logger.info("WS client disconnected for task %s", task_id)

    async def broadcast(self, task_id: str, message: WSMessage):
        if task_id not in self._connections:
            return
        data = message.model_dump_json()
        dead = []
        for ws in self._connections[task_id]:
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(task_id, ws)

    async def handle_client(self, task_id: str, ws: WebSocket):
        await self.connect(task_id, ws)
        cmd_queue = self.get_command_queue(task_id)
        try:
            while True:
                raw = await ws.receive_text()
                try:
                    msg = json.loads(raw)
                    cmd_type = msg.get("type", "")
                    payload = msg.get("payload", {})
                    await cmd_queue.put(cmd_type, payload)
                    await ws.send_text(WSMessage(type="status", payload={"ack": cmd_type}).model_dump_json())
                except json.JSONDecodeError:
                    await ws.send_text(WSMessage(type="status", payload={"error": "invalid JSON"}).model_dump_json())
        except WebSocketDisconnect:
            self.disconnect(task_id, ws)

    def cleanup(self, task_id: str):
        self._connections.pop(task_id, None)
        self._command_queues.pop(task_id, None)
