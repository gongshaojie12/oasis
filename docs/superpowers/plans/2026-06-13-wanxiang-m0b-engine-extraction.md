# 万象 WANXIANG · M0-B-1 引擎机制层抽取（Channel / Clock）实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** 把 OASIS 中平台无关、零业务逻辑的"机制层"组件（`Channel` 异步消息、`Clock` 沙盒时钟）抽取为独立的 `engine/` 包，确立"机制层与平台业务分离"的结构基石，同时保证 OASIS 仍能完整导入、现有测试基线不被破坏。

**Architecture:** `engine/` 成为 OASIS fork 后的内核机制层（spec §3.1 的 ①）。本计划用"移动 + 兼容再导出"策略：把 `Channel`/`Clock` 物理移到 `engine/`，在原 `oasis` 位置保留 thin re-export，使现有 `oasis` 代码与测试零改动继续工作。这样既建立了新结构，又不破坏存量。

**Tech Stack:** Python 3.11（oasis conda 环境），pytest。运行解释器固定为 `/d/software/conda_data/envs/oasis/python.exe`（本机 shell 无 `poetry`/可用 `python`，详见项目记忆 python-env）。

这是 M0-B 的**第一个子计划**。后续：M0-B-2（抽取 `running()` 分发循环 + trace 机制为 `engine/orchestrator.py`、`engine/trace.py`），M0-B-3（把 `platform.py` 的 30 个动作业务逻辑迁入 dialect 执行体）。每个独立成计划。

## 基线说明（重要）
执行前 `test/infra/database/` 有 6 个测试因 **Windows SQLite teardown 文件锁（WinError 32）** 预存失败，与本计划无关。本计划只需保证：(a) 这 6 个失败数不增加；(b) `import oasis` 仍成功；(c) `Channel`/`Clock` 在新旧两处都能导入且行为一致。

---

## 文件结构

- `engine/__init__.py` — 新建，引擎包初始化（导出 Channel, Clock）
- `engine/channel.py` — 从 `oasis/social_platform/channel.py` 移入（内容不变，仅版权头说明来源）
- `engine/clock.py` — 从 `oasis/clock/clock.py` 移入（内容不变）
- `oasis/social_platform/channel.py` — 改为 thin re-export（`from engine.channel import *`）
- `oasis/clock/clock.py` — 改为 thin re-export（`from engine.clock import Clock`）
- `test/wanxiang/test_engine_channel.py` — 新建，验证 engine.Channel 行为
- `test/wanxiang/test_engine_clock.py` — 新建，验证 engine.Clock 行为
- `test/wanxiang/test_engine_backcompat.py` — 新建，验证旧导入路径仍可用且与新路径是同一对象

---

## Task 1: 建立 engine 包并抽取 Channel

**Files:**
- Create: `engine/__init__.py`
- Create: `engine/channel.py`
- Test: `test/wanxiang/test_engine_channel.py`

- [ ] **Step 1: 写失败测试**

`test/wanxiang/test_engine_channel.py`：
```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import asyncio

import pytest

from engine.channel import Channel, AsyncSafeDict


def test_channel_roundtrip():
    async def scenario():
        ch = Channel()
        # 写入接收队列，拿到 message_id
        mid = await ch.write_to_receive_queue(("agent", "payload", "create_post"))
        # 消费端读到同一条
        got_id, info = await ch.receive_from()
        assert got_id == mid
        assert info == ("agent", "payload", "create_post")
        # 平台回写结果，发起端读到
        await ch.send_to((mid, 1, {"success": True}))
        result = await ch.read_from_send_queue(mid)
        assert result == (mid, 1, {"success": True})

    asyncio.run(scenario())


def test_async_safe_dict_basic():
    async def scenario():
        d = AsyncSafeDict()
        await d.put("k", 1)
        assert await d.get("k") == 1
        assert await d.keys() == ["k"]
        assert await d.pop("k") == 1
        assert await d.get("k") is None

    asyncio.run(scenario())
```

- [ ] **Step 2: 运行确认失败**

Run: `/d/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_engine_channel.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'engine'`

- [ ] **Step 3: 创建 engine 包**

`engine/__init__.py`：
```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""engine: 平台无关的模拟内核机制层。

由 OASIS (Apache 2.0, CAMEL-AI.org) 的机制组件抽取重构而来；
平台业务逻辑不在此层。详见 docs/superpowers/specs 的系统设计。
"""
from engine.channel import Channel, AsyncSafeDict
from engine.clock import Clock

__all__ = ["Channel", "AsyncSafeDict", "Clock"]
```

> 注意：`engine/__init__.py` 同时 import `engine.clock`，而 `engine/clock.py` 在 Task 2 才创建。因此本 Task 先**不要**让测试通过 `engine/__init__.py` 触发 clock 导入——测试用的是 `from engine.channel import ...`（直接导子模块，不经过包 __init__ 的 clock 行）。但 Python 导入子模块时会先执行包的 `__init__.py`！为避免顺序问题：本 Task 的 `engine/__init__.py` 先只导 channel，Task 2 再补 clock。

本 Task 的 `engine/__init__.py` 实际写成（仅 channel）：
```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""engine: 平台无关的模拟内核机制层。

由 OASIS (Apache 2.0, CAMEL-AI.org) 的机制组件抽取重构而来；
平台业务逻辑不在此层。详见 docs/superpowers/specs 的系统设计。
"""
from engine.channel import Channel, AsyncSafeDict

__all__ = ["Channel", "AsyncSafeDict"]
```
（Task 2 会把 Clock 加进来。）

- [ ] **Step 4: 移入 channel.py**

把 `oasis/social_platform/channel.py` 的**完整内容**复制为 `engine/channel.py`，仅在文件顶部 docstring/注释处补一句来源说明。`engine/channel.py` 内容：
```python
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Moved into engine/ (WANXIANG) from oasis/social_platform/channel.py — content unchanged.
import asyncio
import uuid


class AsyncSafeDict:

    def __init__(self):
        self.dict = {}
        self.lock = asyncio.Lock()

    async def put(self, key, value):
        async with self.lock:
            self.dict[key] = value

    async def get(self, key, default=None):
        async with self.lock:
            return self.dict.get(key, default)

    async def pop(self, key, default=None):
        async with self.lock:
            return self.dict.pop(key, default)

    async def keys(self):
        async with self.lock:
            return list(self.dict.keys())


class Channel:

    def __init__(self):
        self.receive_queue = asyncio.Queue()  # Used to store received messages
        # Using an asynchronous safe dictionary to store messages to be sent
        self.send_dict = AsyncSafeDict()

    async def receive_from(self):
        message = await self.receive_queue.get()
        return message

    async def send_to(self, message):
        # message_id is the first element of the message
        message_id = message[0]
        await self.send_dict.put(message_id, message)

    async def write_to_receive_queue(self, action_info):
        message_id = str(uuid.uuid4())
        await self.receive_queue.put((message_id, action_info))
        return message_id

    async def read_from_send_queue(self, message_id):
        while True:
            if message_id in await self.send_dict.keys():
                # Attempting to retrieve the message
                message = await self.send_dict.pop(message_id, None)
                if message:
                    return message  # Return the found message
            # Temporarily suspend to avoid tight looping
            await asyncio.sleep(
                0.1)  # set a large one to reduce the workload of cpu
```

- [ ] **Step 5: 运行确认通过**

Run: `/d/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_engine_channel.py -v`
Expected: PASS（2 passed）

- [ ] **Step 6: Commit**

```bash
cd "D:\NLp\oasis"
git add engine/__init__.py engine/channel.py test/wanxiang/test_engine_channel.py
git commit -m "feat(engine): extract Channel into engine/ mechanism layer"
```
End commit message with trailing blank line then:
Co-Authored-By: Claude <noreply@anthropic.com>

---

## Task 2: 抽取 Clock 并补全 engine 包导出

**Files:**
- Create: `engine/clock.py`
- Modify: `engine/__init__.py`（加入 Clock）
- Test: `test/wanxiang/test_engine_clock.py`

- [ ] **Step 1: 写失败测试**

`test/wanxiang/test_engine_clock.py`：
```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
from datetime import datetime, timedelta

from engine.clock import Clock


def test_clock_get_time_step_starts_at_zero():
    c = Clock(k=60)
    assert c.get_time_step() == "0"
    c.time_step += 1
    assert c.get_time_step() == "1"


def test_clock_time_transfer_scales_elapsed():
    # k=2：相对真实起点流逝的时间被放大 2 倍后叠加到 start_time
    c = Clock(k=2)
    start = datetime(2026, 1, 1, 0, 0, 0)
    # 构造一个"现在" = 真实起点 + 10 秒
    now = c.real_start_time + timedelta(seconds=10)
    result = c.time_transfer(now, start)
    # 期望：start + 2*10 秒
    assert result == start + timedelta(seconds=20)


def test_clock_default_k_is_one():
    c = Clock()
    assert c.k == 1
```

- [ ] **Step 2: 运行确认失败**

Run: `/d/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_engine_clock.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'engine.clock'`

- [ ] **Step 3: 移入 clock.py**

`engine/clock.py`（内容同 `oasis/clock/clock.py`，仅补来源注释）：
```python
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Moved into engine/ (WANXIANG) from oasis/clock/clock.py — content unchanged.
from datetime import datetime


class Clock:
    r"""Clock used for the sandbox."""

    def __init__(self, k: int = 1):
        self.real_start_time = datetime.now()
        self.k = k
        self.time_step = 0

    def time_transfer(self, now_time: datetime,
                      start_time: datetime) -> datetime:
        time_diff = now_time - self.real_start_time
        adjusted_diff = self.k * time_diff
        adjusted_time = start_time + adjusted_diff
        return adjusted_time

    def get_time_step(self) -> str:
        return str(self.time_step)
```

- [ ] **Step 4: 补全 engine/__init__.py**

把 `engine/__init__.py` 改为：
```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""engine: 平台无关的模拟内核机制层。

由 OASIS (Apache 2.0, CAMEL-AI.org) 的机制组件抽取重构而来；
平台业务逻辑不在此层。详见 docs/superpowers/specs 的系统设计。
"""
from engine.channel import Channel, AsyncSafeDict
from engine.clock import Clock

__all__ = ["Channel", "AsyncSafeDict", "Clock"]
```

- [ ] **Step 5: 运行确认通过**

Run: `/d/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_engine_clock.py -v`
Expected: PASS（3 passed）

- [ ] **Step 6: Commit**

```bash
cd "D:\NLp\oasis"
git add engine/clock.py engine/__init__.py test/wanxiang/test_engine_clock.py
git commit -m "feat(engine): extract Clock and complete engine package exports"
```
End commit message with trailing blank line then:
Co-Authored-By: Claude <noreply@anthropic.com>

---

## Task 3: 旧路径改为兼容再导出 + 回归验证

把 OASIS 原位置改成从 engine 再导出，保证现有 oasis 代码与 54 个存量测试零改动继续工作。

**Files:**
- Modify: `oasis/social_platform/channel.py`（改为 re-export）
- Modify: `oasis/clock/clock.py`（改为 re-export）
- Test: `test/wanxiang/test_engine_backcompat.py`

- [ ] **Step 1: 写失败测试**

`test/wanxiang/test_engine_backcompat.py`：
```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""验证旧导入路径仍可用，且与 engine 是同一个类对象（确认是再导出而非副本）。"""


def test_old_channel_path_is_engine_channel():
    from engine.channel import Channel as EngineChannel
    from oasis.social_platform.channel import Channel as OasisChannel
    assert OasisChannel is EngineChannel


def test_old_clock_path_is_engine_clock():
    from engine.clock import Clock as EngineClock
    from oasis.clock.clock import Clock as OasisClock
    assert OasisClock is EngineClock


def test_oasis_still_imports():
    import oasis
    assert oasis.__version__
```

- [ ] **Step 2: 运行确认失败**

Run: `/d/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_engine_backcompat.py -v`
Expected: 前两个 FAIL（`OasisChannel is EngineChannel` 为 False，因为此时还是各自独立的类定义）；第三个可能 PASS。

- [ ] **Step 3: 改 oasis/social_platform/channel.py 为再导出**

整个文件替换为：
```python
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Compatibility shim: Channel was moved to engine/ (WANXIANG refactor).
# Import from engine.channel; this re-export keeps existing oasis imports working.
from engine.channel import AsyncSafeDict, Channel  # noqa: F401

__all__ = ["Channel", "AsyncSafeDict"]
```

- [ ] **Step 4: 改 oasis/clock/clock.py 为再导出**

整个文件替换为：
```python
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Compatibility shim: Clock was moved to engine/ (WANXIANG refactor).
from engine.clock import Clock  # noqa: F401

__all__ = ["Clock"]
```

- [ ] **Step 5: 运行确认通过**

Run: `/d/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_engine_backcompat.py -v`
Expected: PASS（3 passed）

- [ ] **Step 6: 回归——oasis 导入 + 全 wanxiang 套件 + 存量基线不退化**

Run: `/d/software/conda_data/envs/oasis/python.exe -c "import oasis; from oasis.social_platform.channel import Channel; from oasis.clock.clock import Clock; print('oasis re-export OK')"`
Expected: 打印 `oasis re-export OK`

Run: `/d/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/ -q`
Expected: 38 + 2 + 3 + 3 = 46 passed

Run（存量基线，确认未新增失败）: `/d/software/conda_data/envs/oasis/python.exe -m pytest test/infra/recsys -q`
Expected: 与重构前一致（recsys 测试不依赖被移动的 Channel/Clock，应全 PASS 或与基线相同）。若出现 **新的** 失败（非 WinError 32 文件锁类），报 BLOCKED。

- [ ] **Step 7: Commit**

```bash
cd "D:\NLp\oasis"
git add oasis/social_platform/channel.py oasis/clock/clock.py test/wanxiang/test_engine_backcompat.py
git commit -m "refactor(oasis): re-export Channel/Clock from engine (back-compat shim)"
```
End commit message with trailing blank line then:
Co-Authored-By: Claude <noreply@anthropic.com>

---

## 完成标准（Definition of Done）

- [ ] `engine/` 包存在，导出 `Channel`、`AsyncSafeDict`、`Clock`
- [ ] `from oasis.social_platform.channel import Channel` 与 `from engine.channel import Channel` 是**同一对象**
- [ ] `import oasis` 成功
- [ ] `test/wanxiang/` 全绿（46 passed）
- [ ] `test/infra/recsys` 无新增失败（对照基线）
- [ ] `test/infra/database` 的失败数不超过基线的 6 个（WinError 32 文件锁，预存问题）

## 下一个计划（不在本计划范围）
- **M0-B-2**：抽取 `Platform.running()` 分发循环与 `_record_trace` 等为 `engine/orchestrator.py` + `engine/trace.py`。
- **M0-B-3**：把 `platform.py` 的 30 个动作业务逻辑迁入 dialect 执行体，由 wanxiang 三层动作空间驱动。
