# 万象 WANXIANG · M0-B-2 编排分发与 trace 机制抽取 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** 把 OASIS `Platform.running()` 里平台无关的"动作分发机制"（按名查 handler + 按参数个数构建调用）抽取为 `engine/orchestrator.py` 的 `dispatch_action()`，把 `PlatformUtils._record_trace()` 里的 trace 写入语句构建抽取为 `engine/trace.py` 的 `build_trace_insert()`，并重接 OASIS 调用——行为完全不变，机制层下沉到 `engine/`。

**Architecture:** 延续 M0-B-1 的"抽机制 + 原地重接"策略。`dispatch_action(handler_owner, action_name, agent_id, message)` 用 `getattr` 在传入对象上找异步方法并按其参数个数（1/2/3，含 self）构建调用，与原 `running()` 内联逻辑逐字等价；`Platform.running()` 改为调用它。`build_trace_insert(user_id, current_time, action_type, action_info)` 返回 `(sql, params)`，`_record_trace` 改为用它。两者均纯函数/可独立单测。

**Tech Stack:** Python 3.11（oasis conda 环境）。运行解释器固定 `/d/software/conda_data/envs/oasis/python.exe`（见记忆 python-env）。

M0-B 第二个子计划。基线：执行前 `test/infra/database/` 有 6 failed + 2 errors（Windows SQLite 文件锁 WinError 32，预存，与本计划无关）；`test/wanxiang/` 46 passed；`import oasis` OK。本计划须保证这些不退化。

---

## 文件结构
- `engine/orchestrator.py` — 新建，`dispatch_action()`
- `engine/trace.py` — 新建，`build_trace_insert()`
- `engine/__init__.py` — 修改，导出 `dispatch_action`, `build_trace_insert`
- `oasis/social_platform/platform.py` — 修改 `running()`，改用 `dispatch_action`（仅替换分发段，EXIT 生命周期逻辑保留）
- `oasis/social_platform/platform_utils.py` — 修改 `_record_trace()`，改用 `build_trace_insert`
- `test/wanxiang/test_engine_orchestrator.py` — 新建
- `test/wanxiang/test_engine_trace.py` — 新建
- `test/wanxiang/test_engine_rewire.py` — 新建

---

## Task 1: 抽取 dispatch_action

**Files:**
- Create: `engine/orchestrator.py`
- Test: `test/wanxiang/test_engine_orchestrator.py`

- [ ] **Step 1: 写失败测试**

`test/wanxiang/test_engine_orchestrator.py`：
```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import asyncio

import pytest

from engine.orchestrator import dispatch_action


class FakeOwner:
    """模拟 Platform：含不同参数个数的异步动作方法。"""

    async def refresh(self, agent_id):           # 2 params (self, agent_id)
        return {"ok": "refresh", "agent": agent_id}

    async def create_post(self, agent_id, content):  # 3 params
        return {"ok": "post", "agent": agent_id, "content": content}

    async def update_rec_table(self):            # 1 param (self only)
        return {"ok": "rec"}


def test_dispatch_two_param_action_passes_agent_id():
    owner = FakeOwner()
    r = asyncio.run(dispatch_action(owner, "refresh", agent_id=7, message=None))
    assert r == {"ok": "refresh", "agent": 7}


def test_dispatch_three_param_action_passes_message_as_second():
    owner = FakeOwner()
    r = asyncio.run(
        dispatch_action(owner, "create_post", agent_id=3, message="hello"))
    assert r == {"ok": "post", "agent": 3, "content": "hello"}


def test_dispatch_one_param_action_ignores_agent_and_message():
    owner = FakeOwner()
    r = asyncio.run(
        dispatch_action(owner, "update_rec_table", agent_id=99, message="x"))
    assert r == {"ok": "rec"}


def test_dispatch_unknown_action_raises():
    owner = FakeOwner()
    with pytest.raises(ValueError, match="not supported"):
        asyncio.run(dispatch_action(owner, "nonexistent", agent_id=1, message=None))


def test_dispatch_rejects_too_many_params():
    class Bad:
        async def weird(self, agent_id, message, extra):  # 4 params
            return None
    with pytest.raises(ValueError, match="parameters are not"):
        asyncio.run(dispatch_action(Bad(), "weird", agent_id=1, message="m"))
```

- [ ] **Step 2: 运行确认失败**

Run: `/d/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_engine_orchestrator.py -v`
Expected: `ModuleNotFoundError: No module named 'engine.orchestrator'`

- [ ] **Step 3: 实现 orchestrator.py**

`engine/orchestrator.py`：
```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""动作分发机制（平台无关）。

抽取自 OASIS Platform.running() 的内联分发逻辑：按动作名在 handler
对象上查找异步方法，按其参数个数（含 self：1/2/3）构建调用。行为与
原内联逻辑逐字等价。
"""
from __future__ import annotations

from typing import Any


async def dispatch_action(
    handler_owner: Any,
    action_name: str,
    agent_id: Any,
    message: Any,
) -> Any:
    """在 handler_owner 上找名为 action_name 的异步方法并调用。

    参数构建规则（与 OASIS 原逻辑一致，参数个数含 self）：
    - 1 个参数 (仅 self): 不传 agent_id / message
    - 2 个参数 (self, agent_id): 传 agent_id
    - 3 个参数 (self, agent_id, <second>): 传 agent_id + 把 message
      作为第二个业务参数（按其形参名传入）
    - >3 个参数: 不支持，抛 ValueError
    """
    action_function = getattr(handler_owner, action_name, None)
    if action_function is None:
        raise ValueError(f"Action {action_name} is not supported")

    func_code = action_function.__code__
    param_names = func_code.co_varnames[:func_code.co_argcount]
    len_param_names = len(param_names)
    if len_param_names > 3:
        raise ValueError(
            f"Functions with {len_param_names} parameters are not "
            f"supported.")

    params: dict[str, Any] = {}
    if len_param_names >= 2:
        params["agent_id"] = agent_id
    if len_param_names == 3:
        second_param_name = param_names[2]
        params[second_param_name] = message

    return await action_function(**params)
```

- [ ] **Step 4: 运行确认通过**

Run: `/d/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_engine_orchestrator.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
cd "D:\NLp\oasis"
git add engine/orchestrator.py test/wanxiang/test_engine_orchestrator.py
git commit -m "feat(engine): extract dispatch_action orchestration mechanism"
```
End commit message with trailing blank line then:
Co-Authored-By: Claude <noreply@anthropic.com>

---

## Task 2: 抽取 build_trace_insert

**Files:**
- Create: `engine/trace.py`
- Modify: `engine/__init__.py`
- Test: `test/wanxiang/test_engine_trace.py`

- [ ] **Step 1: 写失败测试**

`test/wanxiang/test_engine_trace.py`：
```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import json

from engine.trace import build_trace_insert


def test_build_trace_insert_returns_query_and_params():
    sql, params = build_trace_insert(
        user_id=5, current_time="2026-01-01", action_type="create_post",
        action_info={"content": "hi", "post_id": 1})
    assert "INSERT INTO trace" in sql
    assert "user_id, created_at, action, info" in sql
    assert params[0] == 5
    assert params[1] == "2026-01-01"
    assert params[2] == "create_post"
    assert params[3] == json.dumps({"content": "hi", "post_id": 1})


def test_build_trace_insert_params_is_4_tuple():
    sql, params = build_trace_insert(1, "t", "do_nothing", {})
    assert isinstance(params, tuple)
    assert len(params) == 4
    assert params[3] == "{}"
```

- [ ] **Step 2: 运行确认失败**

Run: `/d/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_engine_trace.py -v`
Expected: `ModuleNotFoundError: No module named 'engine.trace'`

- [ ] **Step 3: 实现 trace.py**

`engine/trace.py`：
```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""trace 行为日志写入构建（平台无关）。

抽取自 OASIS PlatformUtils._record_trace 的 SQL 构建部分。时间计算
（依赖 recsys_type / clock）仍由调用方完成；本函数只负责把字段组装成
可执行的 INSERT 语句与参数。
"""
from __future__ import annotations

import json
from typing import Any


def build_trace_insert(
    user_id: Any,
    current_time: Any,
    action_type: str,
    action_info: Any,
) -> tuple[str, tuple]:
    """返回 (sql, params)，用于向 trace 表插入一条行为日志。

    action_info 会被 json.dumps 序列化为字符串存入 info 列。
    """
    sql = ("INSERT INTO trace (user_id, created_at, action, info) "
           "VALUES (?, ?, ?, ?)")
    params = (user_id, current_time, action_type, json.dumps(action_info))
    return sql, params
```

- [ ] **Step 4: 运行确认通过**

Run: `/d/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_engine_trace.py -v`
Expected: 2 passed

- [ ] **Step 5: 补全 engine/__init__.py**

把 `engine/__init__.py` 改为：
```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""engine: 平台无关的模拟内核机制层。

由 OASIS (Apache 2.0, CAMEL-AI.org) 的机制组件抽取重构而来；
平台业务逻辑不在此层。详见 docs/superpowers/specs 的系统设计。
"""
from engine.channel import Channel, AsyncSafeDict
from engine.clock import Clock
from engine.orchestrator import dispatch_action
from engine.trace import build_trace_insert

__all__ = [
    "Channel", "AsyncSafeDict", "Clock",
    "dispatch_action", "build_trace_insert",
]
```
验证：`/d/software/conda_data/envs/oasis/python.exe -c "from engine import dispatch_action, build_trace_insert, Channel, Clock; print('engine exports OK')"` → 期望 `engine exports OK`

- [ ] **Step 6: Commit**

```bash
cd "D:\NLp\oasis"
git add engine/trace.py engine/__init__.py test/wanxiang/test_engine_trace.py
git commit -m "feat(engine): extract build_trace_insert trace mechanism"
```
End commit message with trailing blank line then:
Co-Authored-By: Claude <noreply@anthropic.com>

---

## Task 3: 重接 OASIS 调用 + 回归

把 OASIS 改为使用 engine 的两个新机制，保证行为完全不变、基线不退化。

**Files:**
- Modify: `oasis/social_platform/platform.py`（`running()` 分发段 + import）
- Modify: `oasis/social_platform/platform_utils.py`（`_record_trace()` + import）
- Test: `test/wanxiang/test_engine_rewire.py`

- [ ] **Step 1: 写回归测试**

`test/wanxiang/test_engine_rewire.py`：
```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""验证 OASIS 重接 engine 机制后仍正常工作。"""
import asyncio
import sqlite3
from datetime import datetime


def test_oasis_imports_after_rewire():
    import oasis
    assert oasis.__version__


def test_record_trace_writes_row(tmp_path):
    from oasis.social_platform.platform_utils import PlatformUtils
    from oasis.social_platform.typing import RecsysType
    from engine.clock import Clock

    db_path = str(tmp_path / "t.db")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("CREATE TABLE trace (user_id INTEGER, created_at TEXT, "
                "action TEXT, info TEXT)")
    conn.commit()

    utils = PlatformUtils(
        db=conn, db_cursor=cur, start_time=datetime.now(),
        sandbox_clock=Clock(k=60), show_score=False,
        recsys_type=RecsysType.TWITTER, report_threshold=1)
    utils._record_trace(1, "create_post", {"content": "hi"})

    cur.execute("SELECT user_id, action, info FROM trace")
    row = cur.fetchone()
    conn.close()
    assert row[0] == 1
    assert row[1] == "create_post"
    assert '"content": "hi"' in row[2]


def test_platform_dispatch_via_orchestrator(tmp_path):
    from oasis.social_platform.platform import Platform
    from oasis.social_platform.typing import ActionType
    from engine.channel import Channel

    db_path = str(tmp_path / "p.db")
    channel = Channel()
    platform = Platform(db_path=db_path, channel=channel,
                        recsys_type="twitter")

    async def scenario():
        task = asyncio.create_task(platform.running())
        mid = await channel.write_to_receive_queue(
            (0, None, ActionType.DO_NOTHING.value))
        resp = await channel.read_from_send_queue(mid)
        await channel.write_to_receive_queue(
            (None, None, ActionType.EXIT.value))
        await task
        return resp

    resp = asyncio.run(scenario())
    assert resp[2]["success"] is True
```

- [ ] **Step 2: 运行记录当前结果**

Run: `/d/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_engine_rewire.py -v`
说明：重接前这些测试可能已 PASS（旧内联逻辑与新机制行为等价）。这是允许的——本 Task 的测试是"重接后不退化"的护栏，重点是 Step 5 重接后仍全 PASS。记录当前结果即可，不要求严格红。

- [ ] **Step 3: 重接 platform.py 的 running()**

在 `oasis/social_platform/platform.py` 的 import 区（与其它 `from oasis...`/`from engine...` import 并列处，约第 25–34 行附近）增加一行：
```python
from engine.orchestrator import dispatch_action
```
然后把 `running()` 方法里 EXIT 分支**之后**的整段分发逻辑（原 `# Retrieve the corresponding function using getattr` 注释到方法结尾，即 `action_function = getattr(...)` 到 `raise ValueError(f"Action {action} is not supported")` 那整段）替换为：
```python
            # Dispatch via the engine orchestration mechanism
            result = await dispatch_action(self, action.value, agent_id,
                                           message)
            await self.channel.send_to((message_id, agent_id, result))
```
替换后整个 `running()` 应为：
```python
    async def running(self):
        while True:
            message_id, data = await self.channel.receive_from()

            agent_id, message, action = data
            action = ActionType(action)

            if action == ActionType.EXIT:
                # If the database is in-memory, save it to a file before
                # losing
                if self.db_path == ":memory:":
                    dst = sqlite3.connect("mock.db")
                    with dst:
                        self.db.backup(dst)

                self.db_cursor.close()
                self.db.close()
                break

            # Dispatch via the engine orchestration mechanism
            result = await dispatch_action(self, action.value, agent_id,
                                           message)
            await self.channel.send_to((message_id, agent_id, result))
```
`run()` 方法（`asyncio.run(self.running())`）保持不变。

- [ ] **Step 4: 重接 platform_utils.py 的 _record_trace()**

在 `oasis/social_platform/platform_utils.py` 顶部 import 区（约 14–17 行）增加：
```python
from engine.trace import build_trace_insert
```
把 `_record_trace` 方法里**构建并执行 SQL 的部分**（原 `trace_insert_query = (...)` 到 `self._execute_db_command(...)` 调用，含 `action_info_str = json.dumps(...)` 那行）替换为：
```python
        trace_insert_query, trace_params = build_trace_insert(
            user_id, current_time, action_type, action_info)
        self._execute_db_command(trace_insert_query, trace_params,
                                 commit=True)
```
时间计算逻辑（`if self.recsys_type == RecsysType.REDDIT: ... else: ...`）保持不变。`import json` 不要删除（即使本文件其它处可能不再用它，保留以降低风险）。替换后 `_record_trace` 应为：
```python
    def _record_trace(self,
                      user_id,
                      action_type,
                      action_info,
                      current_time=None):
        r"""If, in addition to the trace, the operation function also records
        time in other tables of the database, use the time of entering
        the operation function for consistency.

        Pass in current_time to make, for example, the created_at in the post
        table exactly the same as the time in the trace table.

        If only the trace table needs to record time, use the entry time into
        _record_trace as the time for the trace record.
        """
        if self.recsys_type == RecsysType.REDDIT:
            current_time = self.sandbox_clock.time_transfer(
                datetime.now(), self.start_time)
        else:
            current_time = self.sandbox_clock.get_time_step()

        trace_insert_query, trace_params = build_trace_insert(
            user_id, current_time, action_type, action_info)
        self._execute_db_command(trace_insert_query, trace_params,
                                 commit=True)
```

- [ ] **Step 5: 运行确认重接后全绿**

Run: `/d/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_engine_rewire.py -v`
Expected: 3 passed

- [ ] **Step 6: 回归——不退化**

Run: `/d/software/conda_data/envs/oasis/python.exe -c "import oasis; print('oasis OK', oasis.__version__)"`
Expected: `oasis OK 0.2.5`

Run: `/d/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/ -q`
Expected: 46 + 5 + 2 + 3 = 56 passed

Run: `/d/software/conda_data/envs/oasis/python.exe -m pytest test/infra/recsys -q`
Expected: 全 PASS（与基线一致）

Run（基线对照）: `/d/software/conda_data/envs/oasis/python.exe -m pytest test/infra/database -q 2>&1 | tail -3`
Expected: 失败/错误数 **不超过** 基线（6 failed + 2 errors，均 WinError 32 文件锁）。若出现**新的非文件锁失败**，报 BLOCKED。

- [ ] **Step 7: Commit**

```bash
cd "D:\NLp\oasis"
git add oasis/social_platform/platform.py oasis/social_platform/platform_utils.py test/wanxiang/test_engine_rewire.py
git commit -m "refactor(oasis): rewire running()/record_trace to engine mechanisms"
```
End commit message with trailing blank line then:
Co-Authored-By: Claude <noreply@anthropic.com>

---

## 完成标准（Definition of Done）
- [ ] `engine/` 导出 `dispatch_action`, `build_trace_insert`（连同已有 Channel/AsyncSafeDict/Clock）
- [ ] `Platform.running()` 经由 `dispatch_action` 分发；`_record_trace` 经由 `build_trace_insert` 构建
- [ ] `import oasis` 成功
- [ ] `test/wanxiang/` 56 passed
- [ ] `test/infra/recsys` 无新增失败
- [ ] `test/infra/database` 失败数 ≤ 基线（6 failed + 2 errors，WinError 32）
- [ ] 端到端 do_nothing 经 Channel→running→dispatch_action 正常回写

## 下一个计划（不在本范围）
- **M0-B-3**：把 `platform.py` 的 30 个动作业务逻辑迁入 dialect 执行体，由 wanxiang 三层动作空间驱动。
