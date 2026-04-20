# P3-2 Live Control Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade simulation monitoring with WebSocket bi-directional communication, supporting real-time control (pause/resume/speed/inject), live data streaming, and a dedicated control panel for running simulations.

**Architecture:** Engine adds WebSocket handler with command protocol. SimulationRunner gets a command queue checked each round. Nuxt proxy exposes a WS endpoint. Frontend adds `useWebSocket` composable (wrapping SSE as fallback), `LiveControlPanel`, `PostStream`, and `EventInjector` components. SSE is kept as degradation fallback.

**Tech Stack:** FastAPI WebSocket (engine), h3/Nuxt WS proxy (server), Vue 3 + Naive UI (frontend)

---

### Task 1: Engine — WebSocket Protocol + Command Handler

**Files:**
- Create: `engine/websocket/__init__.py`
- Create: `engine/websocket/protocol.py`
- Create: `engine/websocket/commands.py`

- [ ] **Step 1: Create protocol models**

Create `engine/websocket/protocol.py`:

```python
from __future__ import annotations
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel
import time


class MessageType(str, Enum):
    COMMAND = "command"
    EVENT = "event"
    DATA = "data"
    STATUS = "status"


class WSMessage(BaseModel):
    type: str
    payload: dict[str, Any] = {}
    timestamp: float = 0.0

    def __init__(self, **data):
        if "timestamp" not in data or data["timestamp"] == 0.0:
            data["timestamp"] = time.time()
        super().__init__(**data)


class CommandType(str, Enum):
    PAUSE = "command:pause"
    RESUME = "command:resume"
    SPEED = "command:speed"
    INJECT = "command:inject"
    STEP = "command:step"


class DataType(str, Enum):
    POST = "data:post"
    ACTION = "data:action"
    METRICS = "data:metrics"
    HEALTH = "data:health"
```

- [ ] **Step 2: Create command handler**

Create `engine/websocket/commands.py`:

```python
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
```

Create `engine/websocket/__init__.py`:

```python
from engine.websocket.protocol import WSMessage, CommandType, DataType
from engine.websocket.commands import CommandQueue

__all__ = ["WSMessage", "CommandType", "DataType", "CommandQueue"]
```

- [ ] **Step 3: Commit**

```bash
git add engine/websocket/__init__.py engine/websocket/protocol.py engine/websocket/commands.py
git commit -m "feat(live-control): add WebSocket protocol and command handler"
```

---

### Task 2: Engine — WebSocket Endpoint

**Files:**
- Create: `engine/websocket/handler.py`
- Modify: `engine/main.py` (add WS endpoint)

- [ ] **Step 1: Create WebSocket handler**

Create `engine/websocket/handler.py`:

```python
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

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
```

- [ ] **Step 2: Add WS endpoint to engine/main.py**

Add import at top:
```python
from fastapi import Depends, FastAPI, Header, HTTPException, Request, WebSocket
```

Add after lifespan setup (after `app.state.queue_manager = queue_manager`):
```python
from engine.websocket.handler import SimulationWSManager
app.state.ws_manager = SimulationWSManager()
```

Add WS endpoint at end of file:
```python
@app.websocket("/engine/ws/{task_id}")
async def ws_simulation(websocket: WebSocket, task_id: str):
    ws_manager: SimulationWSManager = websocket.app.state.ws_manager
    await ws_manager.handle_client(task_id, websocket)
```

- [ ] **Step 3: Commit**

```bash
git add engine/websocket/handler.py engine/main.py
git commit -m "feat(live-control): add WebSocket endpoint and connection manager"
```

---

### Task 3: Frontend — useWebSocket Composable + i18n

**Files:**
- Create: `web/app/composables/useWebSocket.ts`
- Modify: `web/locales/zh-CN.json`
- Modify: `web/locales/en-US.json`

- [ ] **Step 1: Create useWebSocket composable**

Create `web/app/composables/useWebSocket.ts`:

```typescript
import { ref, onUnmounted } from 'vue'

export interface WSEvent {
  type: string
  payload: Record<string, any>
  timestamp: number
}

export function useWebSocket(simulationId: string, engineTaskId?: string) {
  const connected = ref(false)
  const status = ref('pending')
  const progress = ref(0)
  const currentStep = ref(0)
  const totalSteps = ref(0)
  const error = ref<string | null>(null)
  const posts = ref<any[]>([])
  const metrics = ref<any>(null)
  const health = ref<any>(null)
  const lastEvent = ref<WSEvent | null>(null)

  let ws: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null

  const authStore = useAuthStore()

  function connect() {
    if (ws) disconnect()

    const taskId = engineTaskId || simulationId
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const url = `${protocol}//${location.host}/api/simulations/${simulationId}/ws?token=${authStore.token}`

    ws = new WebSocket(url)

    ws.onopen = () => {
      connected.value = true
    }

    ws.onmessage = (event) => {
      try {
        const data: WSEvent = JSON.parse(event.data)
        lastEvent.value = data

        if (data.type === 'status') {
          if (data.payload.status) status.value = data.payload.status
          if (data.payload.progress !== undefined) progress.value = data.payload.progress
          if (data.payload.round !== undefined) currentStep.value = data.payload.round
        } else if (data.type === 'data:post') {
          posts.value.unshift(data.payload.post || data.payload)
          if (posts.value.length > 100) posts.value.pop()
        } else if (data.type === 'data:metrics') {
          metrics.value = data.payload
        } else if (data.type === 'data:health') {
          health.value = data.payload
        } else if (data.type === 'data:action') {
          // Action events for logging
        }
      } catch {}
    }

    ws.onerror = () => {
      connected.value = false
    }

    ws.onclose = () => {
      connected.value = false
      if (status.value === 'running' || status.value === 'pending') {
        reconnectTimer = setTimeout(() => connect(), 3000)
      }
    }
  }

  function disconnect() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (ws) {
      ws.close()
      ws = null
    }
    connected.value = false
  }

  function send(type: string, payload: Record<string, any> = {}) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type, payload, timestamp: Date.now() }))
    }
  }

  function pause() { send('command:pause') }
  function resume() { send('command:resume') }
  function setSpeed(speed: number) { send('command:speed', { speed }) }
  function inject(content: string, agentId?: number) { send('command:inject', { content, agent_id: agentId }) }
  function step() { send('command:step') }

  onUnmounted(() => disconnect())

  return {
    connected, status, progress, currentStep, totalSteps, error,
    posts, metrics, health, lastEvent,
    connect, disconnect, send,
    pause, resume, setSpeed, inject, step,
  }
}
```

- [ ] **Step 2: Add i18n keys**

Add `"liveControl"` section to both locale files.

zh-CN:
```json
"liveControl": {
  "title": "直播控制台",
  "connected": "已连接",
  "disconnected": "未连接",
  "pause": "暂停",
  "resume": "恢复",
  "speed": "速度",
  "step": "单步执行",
  "postStream": "实时帖子流",
  "noPosts": "暂无帖子",
  "injectEvent": "注入事件",
  "injectPlaceholder": "输入要注入的事件内容...",
  "injectBtn": "注入",
  "injectSuccess": "事件注入成功",
  "speedLabel": "仿真速度",
  "currentRound": "当前轮次",
  "controlPanel": "控制面板",
  "dataStream": "数据流",
  "eventHistory": "事件历史"
}
```

en-US:
```json
"liveControl": {
  "title": "Live Control Panel",
  "connected": "Connected",
  "disconnected": "Disconnected",
  "pause": "Pause",
  "resume": "Resume",
  "speed": "Speed",
  "step": "Step",
  "postStream": "Live Post Stream",
  "noPosts": "No posts yet",
  "injectEvent": "Inject Event",
  "injectPlaceholder": "Enter event content to inject...",
  "injectBtn": "Inject",
  "injectSuccess": "Event injected",
  "speedLabel": "Simulation Speed",
  "currentRound": "Current Round",
  "controlPanel": "Control Panel",
  "dataStream": "Data Stream",
  "eventHistory": "Event History"
}
```

- [ ] **Step 3: Commit**

```bash
git add web/app/composables/useWebSocket.ts web/locales/zh-CN.json web/locales/en-US.json
git commit -m "feat(live-control): add useWebSocket composable and i18n keys"
```

---

### Task 4: Frontend — LiveControlPanel + PostStream + EventInjector Components

**Files:**
- Create: `web/app/components/live/LiveControlPanel.vue`
- Create: `web/app/components/live/PostStream.vue`
- Create: `web/app/components/live/EventInjector.vue`

- [ ] **Step 1: Create LiveControlPanel**

Main control panel with pause/resume buttons, speed selector (0.5x/1x/2x/4x), single step button, connection status indicator. Uses useWebSocket composable. Props: `simulationId: string`.

- [ ] **Step 2: Create PostStream**

Scrolling post feed showing real-time posts. Props: `posts: any[]`. Each post card shows agent name, content, timestamp, action type.

- [ ] **Step 3: Create EventInjector**

Event injection form with textarea + inject button. Optional agent ID field. Props: inject function from useWebSocket.

- [ ] **Step 4: Commit**

```bash
git add web/app/components/live/LiveControlPanel.vue web/app/components/live/PostStream.vue web/app/components/live/EventInjector.vue
git commit -m "feat(live-control): add LiveControlPanel, PostStream, and EventInjector components"
```

---

### Task 5: Frontend — Integrate into Simulation Detail Page

**Files:**
- Modify: `web/app/pages/simulations/[id].vue`

- [ ] **Step 1: Add live control panel to running simulations**

When simulation is running, show the LiveControlPanel, PostStream, and EventInjector below the existing status card. Import useWebSocket and conditionally connect WS instead of SSE for running sims.

- [ ] **Step 2: Commit**

```bash
git add web/app/pages/simulations/[id].vue
git commit -m "feat(live-control): integrate live control panel into simulation detail page"
```
