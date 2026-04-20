# P1-2: 时间机器 (Time Machine) 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为已完成的仿真添加时间轴回溯、Agent 对话、圆桌会议和情境重放功能，用户可以"穿越"到任意轮次查看快照、与 Agent 对话、发起多 Agent 讨论，或以动画方式回放仿真过程。

**Architecture:** Engine 层提供快照提取（从仿真 SQLite DB 读取 trace/post/user 数据按轮次聚合）和 Agent 对话（基于特定轮次上下文调用 LLM 扮演 Agent）。Web 层新增 3 张表（snapshots/conversations/branches），7 个 API 路由，1 个 Pinia Store，4 个 Vue 组件和 1 个页面。

**Tech Stack:** TypeScript (Nuxt 4, Naive UI, ECharts), Python (FastAPI, Pydantic), Drizzle ORM, Zod

---

## 文件结构

### 新建文件

```
engine/
├── timemachine/
│   ├── __init__.py           — 模块导出
│   ├── snapshot.py           — 快照提取器 (从仿真DB按轮次聚合数据)
│   └── chat.py               — Agent 对话引擎 (LLM角色扮演)

web/
├── server/
│   └── api/timemachine/
│       ├── [simId]/
│       │   ├── snapshots.get.ts      — 获取快照列表
│       │   ├── snapshots/[round].get.ts — 获取特定轮次快照
│       │   ├── chat.post.ts          — 与 Agent 对话
│       │   ├── roundtable.post.ts    — 圆桌会议
│       │   └── replay.get.ts         — 重放数据
├── app/
│   ├── pages/simulations/[id]/
│   │   └── timemachine.vue           — 时间机器主页面
│   ├── components/
│   │   ├── TimelineSlider.vue        — 时间轴滑块
│   │   ├── SnapshotViewer.vue        — 快照查看面板
│   │   ├── AgentChatPanel.vue        — Agent 对话面板
│   │   └── ReplayPlayer.vue          — 情境重放播放器
│   └── stores/
│       └── timemachine.ts            — 时间机器 Pinia Store
```

### 修改文件

```
web/server/database/schema/sqlite.ts   — 新增 simulationSnapshots, agentConversations 表
web/server/database/schema/pg.ts       — 同上 (PostgreSQL 版)
web/server/database/schema/index.ts    — 导出新表
engine/main.py                         — 新增 3 个 Engine API 端点
web/app/pages/simulations/[id].vue     — 添加「时间机器」按钮
web/app/components/layout/Sidebar.vue  — 无需修改 (从仿真详情进入)
```

---

## Task 1: Engine 快照提取器

**Files:**
- Create: `engine/timemachine/__init__.py`
- Create: `engine/timemachine/snapshot.py`
- Test: `engine/tests/test_snapshot.py`

- [ ] **Step 1: 创建快照提取器**

```python
# engine/timemachine/snapshot.py
from __future__ import annotations

import sqlite3
from typing import Any, Optional

from pydantic import BaseModel, Field


class AgentSnapshot(BaseModel):
    agent_id: int
    user_name: str
    post_count: int = 0
    action_count: int = 0
    recent_actions: list[str] = Field(default_factory=list)


class RoundSnapshot(BaseModel):
    round_number: int
    posts: list[dict[str, Any]] = Field(default_factory=list)
    actions: list[dict[str, Any]] = Field(default_factory=list)
    agent_summaries: list[AgentSnapshot] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)


class SnapshotExtractor:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    def extract_all(self, num_steps: int) -> list[RoundSnapshot]:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            snapshots = []
            for round_num in range(1, num_steps + 1):
                snap = self._extract_round(conn, round_num)
                snapshots.append(snap)
            return snapshots
        finally:
            conn.close()

    def extract_round(self, round_number: int) -> RoundSnapshot:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            return self._extract_round(conn, round_number)
        finally:
            conn.close()

    def _extract_round(self, conn: sqlite3.Connection, round_number: int) -> RoundSnapshot:
        cursor = conn.cursor()

        traces = [
            dict(r) for r in cursor.execute(
                "SELECT * FROM trace WHERE info LIKE ?",
                (f'%"step": {round_number}%',),
            ).fetchall()
        ]

        if not traces:
            traces = self._get_traces_by_position(cursor, round_number)

        posts = [
            dict(r) for r in cursor.execute("SELECT * FROM post").fetchall()
        ]
        round_posts = self._filter_posts_for_round(posts, traces)

        users = [dict(r) for r in cursor.execute("SELECT * FROM user").fetchall()]
        agent_summaries = self._build_agent_summaries(users, traces)

        action_counts: dict[str, int] = {}
        for t in traces:
            action = t.get("action", "unknown")
            action_counts[action] = action_counts.get(action, 0) + 1

        metrics = {
            "total_actions": len(traces),
            "total_posts_this_round": len(round_posts),
            "action_distribution": action_counts,
        }

        return RoundSnapshot(
            round_number=round_number,
            posts=round_posts[:50],
            actions=traces[:100],
            agent_summaries=agent_summaries,
            metrics=metrics,
        )

    def _get_traces_by_position(
        self, cursor: sqlite3.Cursor, round_number: int
    ) -> list[dict[str, Any]]:
        all_traces = [dict(r) for r in cursor.execute("SELECT * FROM trace ORDER BY created_at").fetchall()]
        if not all_traces:
            return []

        agent_ids = set(t["user_id"] for t in all_traces)
        num_agents = len(agent_ids)
        if num_agents == 0:
            return []

        start = (round_number - 1) * num_agents
        end = round_number * num_agents
        return all_traces[start:end]

    def _filter_posts_for_round(
        self, all_posts: list[dict[str, Any]], round_traces: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        create_post_user_ids = set()
        for t in round_traces:
            if t.get("action") in ("CREATE_POST", "REPOST", "create_post", "repost"):
                create_post_user_ids.add(t.get("user_id"))

        if not create_post_user_ids:
            return []

        return [p for p in all_posts if p.get("user_id") in create_post_user_ids]

    def _build_agent_summaries(
        self, users: list[dict[str, Any]], round_traces: list[dict[str, Any]]
    ) -> list[AgentSnapshot]:
        agent_actions: dict[int, list[str]] = {}
        for t in round_traces:
            uid = t.get("user_id", 0)
            action = t.get("action", "unknown")
            agent_actions.setdefault(uid, []).append(action)

        user_map = {u["user_id"]: u for u in users}
        summaries = []
        for uid, actions in agent_actions.items():
            user = user_map.get(uid, {})
            summaries.append(AgentSnapshot(
                agent_id=uid,
                user_name=user.get("user_name", f"agent_{uid}"),
                action_count=len(actions),
                recent_actions=actions[:5],
            ))

        summaries.sort(key=lambda s: s.action_count, reverse=True)
        return summaries[:20]
```

- [ ] **Step 2: 创建模块导出**

```python
# engine/timemachine/__init__.py
from engine.timemachine.chat import AgentChatEngine, ChatMessage, ChatResponse
from engine.timemachine.snapshot import (
    AgentSnapshot,
    RoundSnapshot,
    SnapshotExtractor,
)

__all__ = [
    "AgentChatEngine",
    "AgentSnapshot",
    "ChatMessage",
    "ChatResponse",
    "RoundSnapshot",
    "SnapshotExtractor",
]
```

注意：`__init__.py` 中引用了 Task 2 的 `chat.py`，两个任务需要都完成后 `__init__.py` 才能正确导入。先创建占位的 `chat.py` 或延迟到 Task 2 一起处理。

- [ ] **Step 3: 编写测试**

```python
# engine/tests/test_snapshot.py
import os
import sqlite3
import tempfile

import pytest

from engine.timemachine.snapshot import RoundSnapshot, SnapshotExtractor


@pytest.fixture
def sim_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE user (
            user_id INTEGER PRIMARY KEY,
            agent_id INTEGER,
            user_name TEXT,
            name TEXT,
            bio TEXT,
            created_at TEXT,
            num_followings INTEGER DEFAULT 0,
            num_followers INTEGER DEFAULT 0
        );
        CREATE TABLE post (
            post_id INTEGER PRIMARY KEY,
            user_id INTEGER,
            content TEXT,
            created_at TEXT,
            num_likes INTEGER DEFAULT 0,
            num_dislikes INTEGER DEFAULT 0,
            num_shares INTEGER DEFAULT 0
        );
        CREATE TABLE trace (
            user_id INTEGER,
            created_at TEXT,
            action TEXT,
            info TEXT
        );

        INSERT INTO user VALUES (1, 1, 'alice', 'Alice', 'bio', '2026-01-01', 0, 0);
        INSERT INTO user VALUES (2, 2, 'bob', 'Bob', 'bio', '2026-01-01', 0, 0);

        INSERT INTO trace VALUES (1, '2026-01-01 00:01', 'CREATE_POST', '{}');
        INSERT INTO trace VALUES (2, '2026-01-01 00:02', 'LIKE_POST', '{}');
        INSERT INTO trace VALUES (1, '2026-01-01 00:03', 'CREATE_POST', '{}');
        INSERT INTO trace VALUES (2, '2026-01-01 00:04', 'FOLLOW', '{}');

        INSERT INTO post VALUES (1, 1, 'Hello', '2026-01-01 00:01', 0, 0, 0);
        INSERT INTO post VALUES (2, 1, 'World', '2026-01-01 00:03', 0, 0, 0);
    """)
    conn.close()
    yield path
    os.unlink(path)


def test_extract_round(sim_db):
    extractor = SnapshotExtractor(sim_db)
    snap = extractor.extract_round(1)
    assert isinstance(snap, RoundSnapshot)
    assert snap.round_number == 1
    assert snap.metrics["total_actions"] == 2


def test_extract_all(sim_db):
    extractor = SnapshotExtractor(sim_db)
    snaps = extractor.extract_all(2)
    assert len(snaps) == 2
    assert snaps[0].round_number == 1
    assert snaps[1].round_number == 2


def test_agent_summaries(sim_db):
    extractor = SnapshotExtractor(sim_db)
    snap = extractor.extract_round(1)
    assert len(snap.agent_summaries) > 0
    assert snap.agent_summaries[0].user_name in ("alice", "bob")


def test_empty_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE user (user_id INTEGER PRIMARY KEY, agent_id INTEGER, user_name TEXT, name TEXT, bio TEXT, created_at TEXT, num_followings INTEGER DEFAULT 0, num_followers INTEGER DEFAULT 0);
        CREATE TABLE post (post_id INTEGER PRIMARY KEY, user_id INTEGER, content TEXT, created_at TEXT, num_likes INTEGER DEFAULT 0, num_dislikes INTEGER DEFAULT 0, num_shares INTEGER DEFAULT 0);
        CREATE TABLE trace (user_id INTEGER, created_at TEXT, action TEXT, info TEXT);
    """)
    conn.close()
    extractor = SnapshotExtractor(path)
    snap = extractor.extract_round(1)
    assert snap.metrics["total_actions"] == 0
    os.unlink(path)
```

- [ ] **Step 4: 提交**

```bash
git add engine/timemachine/snapshot.py engine/timemachine/__init__.py engine/tests/test_snapshot.py
git commit -m "feat(engine): add snapshot extractor for time machine"
```

---

## Task 2: Engine Agent 对话引擎

**Files:**
- Create: `engine/timemachine/chat.py`
- Test: `engine/tests/test_chat_engine.py`

- [ ] **Step 1: 创建对话引擎**

```python
# engine/timemachine/chat.py
from __future__ import annotations

import sqlite3
from typing import Any, Callable, Awaitable, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str  # "user" or "agent"
    content: str
    agent_id: Optional[int] = None
    agent_name: Optional[str] = None


class ChatResponse(BaseModel):
    agent_id: int
    agent_name: str
    response: str
    context_round: int


class AgentChatEngine:
    def __init__(
        self,
        db_path: str,
        llm_call: Callable[[str], Awaitable[str]],
    ) -> None:
        self._db_path = db_path
        self._llm_call = llm_call

    async def chat(
        self,
        agent_id: int,
        round_context: int,
        user_message: str,
        history: list[ChatMessage] | None = None,
    ) -> ChatResponse:
        agent_profile = self._get_agent_profile(agent_id)
        agent_state = self._get_agent_state_at_round(agent_id, round_context)

        prompt = self._build_chat_prompt(
            agent_profile=agent_profile,
            agent_state=agent_state,
            round_context=round_context,
            user_message=user_message,
            history=history or [],
        )

        response_text = await self._llm_call(prompt)

        return ChatResponse(
            agent_id=agent_id,
            agent_name=agent_profile.get("user_name", f"agent_{agent_id}"),
            response=response_text,
            context_round=round_context,
        )

    async def roundtable(
        self,
        agent_ids: list[int],
        round_context: int,
        topic: str,
        num_rounds: int = 3,
    ) -> list[ChatMessage]:
        profiles = {aid: self._get_agent_profile(aid) for aid in agent_ids}
        states = {aid: self._get_agent_state_at_round(aid, round_context) for aid in agent_ids}

        messages: list[ChatMessage] = []
        for round_num in range(num_rounds):
            for aid in agent_ids:
                prompt = self._build_roundtable_prompt(
                    speaker_profile=profiles[aid],
                    speaker_state=states[aid],
                    all_profiles=profiles,
                    round_context=round_context,
                    topic=topic,
                    prior_messages=messages,
                    round_num=round_num,
                )
                response = await self._llm_call(prompt)
                messages.append(ChatMessage(
                    role="agent",
                    content=response,
                    agent_id=aid,
                    agent_name=profiles[aid].get("user_name", f"agent_{aid}"),
                ))

        return messages

    def _get_agent_profile(self, agent_id: int) -> dict[str, Any]:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute(
                "SELECT * FROM user WHERE user_id = ?", (agent_id,)
            ).fetchone()
            return dict(row) if row else {"user_id": agent_id, "user_name": f"agent_{agent_id}"}
        finally:
            conn.close()

    def _get_agent_state_at_round(self, agent_id: int, round_number: int) -> dict[str, Any]:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            all_traces = [
                dict(r) for r in conn.execute(
                    "SELECT * FROM trace WHERE user_id = ? ORDER BY created_at",
                    (agent_id,),
                ).fetchall()
            ]

            all_agent_ids = set(
                r["user_id"] for r in conn.execute("SELECT DISTINCT user_id FROM trace").fetchall()
            )
            num_agents = max(len(all_agent_ids), 1)
            cutoff = round_number * num_agents

            agent_traces_up_to_round = [t for i, t in enumerate(all_traces) if i < cutoff]

            post_count = sum(
                1 for t in agent_traces_up_to_round
                if t.get("action") in ("CREATE_POST", "REPOST", "create_post", "repost")
            )

            action_counts: dict[str, int] = {}
            for t in agent_traces_up_to_round:
                a = t.get("action", "unknown")
                action_counts[a] = action_counts.get(a, 0) + 1

            recent = agent_traces_up_to_round[-5:] if agent_traces_up_to_round else []

            return {
                "post_count": post_count,
                "total_actions": len(agent_traces_up_to_round),
                "action_distribution": action_counts,
                "recent_actions": [t.get("action", "") for t in recent],
            }
        finally:
            conn.close()

    def _build_chat_prompt(
        self,
        agent_profile: dict[str, Any],
        agent_state: dict[str, Any],
        round_context: int,
        user_message: str,
        history: list[ChatMessage],
    ) -> str:
        name = agent_profile.get("name", agent_profile.get("user_name", "Agent"))
        bio = agent_profile.get("bio", "")

        history_text = ""
        if history:
            lines = []
            for msg in history[-10:]:
                speaker = msg.agent_name if msg.role == "agent" else "用户"
                lines.append(f"{speaker}: {msg.content}")
            history_text = f"\n过往对话:\n" + "\n".join(lines)

        return f"""你现在扮演一个社交媒体仿真中的虚拟用户。

角色信息:
- 名称: {name}
- 简介: {bio}
- 当前是第 {round_context} 轮仿真

截至本轮的状态:
- 发帖数: {agent_state.get('post_count', 0)}
- 总行为数: {agent_state.get('total_actions', 0)}
- 最近行为: {', '.join(agent_state.get('recent_actions', []))}

规则:
1. 你只知道到第 {round_context} 轮为止的信息，不知道之后发生的事
2. 以该角色的身份和视角回答
3. 回答简洁自然，像真实社交媒体用户那样说话
4. 用中文回答
{history_text}

用户提问: {user_message}"""

    def _build_roundtable_prompt(
        self,
        speaker_profile: dict[str, Any],
        speaker_state: dict[str, Any],
        all_profiles: dict[int, dict[str, Any]],
        round_context: int,
        topic: str,
        prior_messages: list[ChatMessage],
        round_num: int,
    ) -> str:
        name = speaker_profile.get("name", speaker_profile.get("user_name", "Agent"))
        bio = speaker_profile.get("bio", "")

        participants = ", ".join(
            p.get("name", p.get("user_name", f"agent_{aid}"))
            for aid, p in all_profiles.items()
        )

        prior_text = ""
        if prior_messages:
            lines = [f"{m.agent_name}: {m.content}" for m in prior_messages[-15:]]
            prior_text = "\n之前的讨论:\n" + "\n".join(lines)

        return f"""你正在参加一场圆桌讨论，扮演社交媒体仿真中的虚拟用户。

你的角色:
- 名称: {name}
- 简介: {bio}
- 当前状态: 发帖 {speaker_state.get('post_count', 0)} 篇, 行为 {speaker_state.get('total_actions', 0)} 次

参与者: {participants}
讨论话题: {topic}
当前是第 {round_num + 1} 轮讨论 (基于仿真第 {round_context} 轮的上下文)
{prior_text}

请以 {name} 的身份发言。要求:
1. 基于你的角色特点和经历发言
2. 回应其他人的观点，可以同意、补充或反驳
3. 简洁有力，2-4 句话
4. 用中文"""
```

- [ ] **Step 2: 编写测试**

```python
# engine/tests/test_chat_engine.py
import os
import sqlite3
import tempfile

import pytest

from engine.timemachine.chat import AgentChatEngine, ChatMessage, ChatResponse


@pytest.fixture
def chat_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE user (
            user_id INTEGER PRIMARY KEY, agent_id INTEGER,
            user_name TEXT, name TEXT, bio TEXT, created_at TEXT,
            num_followings INTEGER DEFAULT 0, num_followers INTEGER DEFAULT 0
        );
        CREATE TABLE trace (
            user_id INTEGER, created_at TEXT, action TEXT, info TEXT
        );

        INSERT INTO user VALUES (1, 1, 'alice', 'Alice', 'Tech enthusiast', '2026-01-01', 5, 10);
        INSERT INTO user VALUES (2, 2, 'bob', 'Bob', 'Sports fan', '2026-01-01', 3, 8);

        INSERT INTO trace VALUES (1, '2026-01-01 00:01', 'CREATE_POST', '{}');
        INSERT INTO trace VALUES (2, '2026-01-01 00:02', 'LIKE_POST', '{}');
        INSERT INTO trace VALUES (1, '2026-01-01 00:03', 'FOLLOW', '{}');
        INSERT INTO trace VALUES (2, '2026-01-01 00:04', 'CREATE_POST', '{}');
    """)
    conn.close()
    yield path
    os.unlink(path)


@pytest.mark.asyncio
async def test_chat_basic(chat_db):
    async def mock_llm(prompt: str) -> str:
        return "I think technology is evolving rapidly."

    engine = AgentChatEngine(db_path=chat_db, llm_call=mock_llm)
    result = await engine.chat(agent_id=1, round_context=1, user_message="What do you think?")

    assert isinstance(result, ChatResponse)
    assert result.agent_id == 1
    assert result.agent_name == "alice"
    assert result.context_round == 1
    assert "technology" in result.response


@pytest.mark.asyncio
async def test_roundtable(chat_db):
    call_count = 0

    async def mock_llm(prompt: str) -> str:
        nonlocal call_count
        call_count += 1
        return f"Response {call_count}"

    engine = AgentChatEngine(db_path=chat_db, llm_call=mock_llm)
    messages = await engine.roundtable(
        agent_ids=[1, 2], round_context=1, topic="Tech trends", num_rounds=2,
    )

    assert len(messages) == 4  # 2 agents * 2 rounds
    assert messages[0].agent_id == 1
    assert messages[1].agent_id == 2
    assert all(m.role == "agent" for m in messages)
```

- [ ] **Step 3: 更新 `__init__.py` 导出**

确保 `engine/timemachine/__init__.py` 包含 Task 1 Step 2 中的完整导出（此时 `chat.py` 已创建）。

- [ ] **Step 4: 提交**

```bash
git add engine/timemachine/chat.py engine/tests/test_chat_engine.py engine/timemachine/__init__.py
git commit -m "feat(engine): add agent chat engine for time machine"
```

---

## Task 3: Engine API 端点

**Files:**
- Modify: `engine/main.py`

- [ ] **Step 1: 添加请求模型和端点**

在 `engine/main.py` 中添加以下内容：

请求模型（添加在现有模型之后）：

```python
class SnapshotRequest(BaseModel):
    db_path: str
    num_steps: int
    round_number: Optional[int] = None  # None = 全部轮次


class AgentChatRequest(BaseModel):
    db_path: str
    agent_id: int
    round_context: int
    message: str
    history: Optional[list[dict[str, Any]]] = None


class RoundtableRequest(BaseModel):
    db_path: str
    agent_ids: list[int]
    round_context: int
    topic: str
    num_rounds: int = Field(default=3, ge=1, le=5)
```

端点（添加在现有端点之后）：

```python
@app.post(
    "/engine/timemachine/snapshots",
    dependencies=[Depends(verify_internal_key)],
)
async def extract_snapshots(body: SnapshotRequest):
    from engine.timemachine.snapshot import SnapshotExtractor

    extractor = SnapshotExtractor(body.db_path)
    if body.round_number is not None:
        snap = extractor.extract_round(body.round_number)
        return {"snapshot": snap.model_dump()}
    else:
        snaps = extractor.extract_all(body.num_steps)
        return {"snapshots": [s.model_dump() for s in snaps]}


@app.post(
    "/engine/timemachine/chat",
    dependencies=[Depends(verify_internal_key)],
)
async def agent_chat(body: AgentChatRequest, request: Request):
    from engine.timemachine.chat import AgentChatEngine, ChatMessage

    settings = request.app.state.settings

    async def llm_call(prompt: str) -> str:
        from engine.llm.provider import LLMProviderRegistry, create_model
        from camel.messages import BaseMessage

        registry = LLMProviderRegistry()
        provider = settings.default_llm_provider or "qwen"
        model_id = settings.default_llm_model or "qwen-plus"
        model = create_model(provider, model_id, settings, registry)
        user_msg = BaseMessage.make_user_message(role_name="user", content=prompt)
        response = model.run([user_msg])
        return response.msgs[0].content

    history = None
    if body.history:
        history = [ChatMessage(**m) for m in body.history]

    engine = AgentChatEngine(db_path=body.db_path, llm_call=llm_call)
    result = await engine.chat(
        agent_id=body.agent_id,
        round_context=body.round_context,
        user_message=body.message,
        history=history,
    )
    return result.model_dump()


@app.post(
    "/engine/timemachine/roundtable",
    dependencies=[Depends(verify_internal_key)],
)
async def roundtable(body: RoundtableRequest, request: Request):
    from engine.timemachine.chat import AgentChatEngine

    settings = request.app.state.settings

    async def llm_call(prompt: str) -> str:
        from engine.llm.provider import LLMProviderRegistry, create_model
        from camel.messages import BaseMessage

        registry = LLMProviderRegistry()
        provider = settings.default_llm_provider or "qwen"
        model_id = settings.default_llm_model or "qwen-plus"
        model = create_model(provider, model_id, settings, registry)
        user_msg = BaseMessage.make_user_message(role_name="user", content=prompt)
        response = model.run([user_msg])
        return response.msgs[0].content

    engine = AgentChatEngine(db_path=body.db_path, llm_call=llm_call)
    messages = await engine.roundtable(
        agent_ids=body.agent_ids,
        round_context=body.round_context,
        topic=body.topic,
        num_rounds=body.num_rounds,
    )
    return {"messages": [m.model_dump() for m in messages]}
```

- [ ] **Step 2: 添加导入**

在 `engine/main.py` 顶部导入区域无需添加顶级导入（使用了 lazy import）。

- [ ] **Step 3: 提交**

```bash
git add engine/main.py
git commit -m "feat(engine): add time machine API endpoints (snapshots, chat, roundtable)"
```

---

## Task 4: 数据库表

**Files:**
- Modify: `web/server/database/schema/sqlite.ts`
- Modify: `web/server/database/schema/pg.ts`
- Modify: `web/server/database/schema/index.ts`

- [ ] **Step 1: 添加 SQLite 表定义**

在 `web/server/database/schema/sqlite.ts` 末尾添加：

```typescript
export const simulationSnapshots = sqliteTable('simulation_snapshots', {
  id: text('id').primaryKey(),
  simulationId: text('simulation_id').notNull().references(() => simulations.id),
  enterpriseId: text('enterprise_id').notNull().references(() => enterprises.id),
  roundNumber: integer('round_number').notNull(),
  snapshotData: text('snapshot_data').notNull(),
  createdAt: text('created_at').notNull(),
})

export const agentConversations = sqliteTable('agent_conversations', {
  id: text('id').primaryKey(),
  simulationId: text('simulation_id').notNull().references(() => simulations.id),
  enterpriseId: text('enterprise_id').notNull().references(() => enterprises.id),
  roundContext: integer('round_context').notNull(),
  conversationType: text('conversation_type').notNull(),  // 'chat' | 'roundtable'
  participants: text('participants').notNull(),  // JSON: agent IDs
  messages: text('messages').notNull(),  // JSON: ChatMessage[]
  topic: text('topic'),
  createdAt: text('created_at').notNull(),
})
```

- [ ] **Step 2: 添加 PostgreSQL 表定义**

在 `web/server/database/schema/pg.ts` 末尾添加等效的 pgTable 定义（结构相同，使用 `pgTable`）。

- [ ] **Step 3: 更新 index.ts 导出**

在 `web/server/database/schema/index.ts` 中添加：

```typescript
export { simulationSnapshots, agentConversations } from './sqlite'
// 或 pg 版本，取决于当前导出模式
```

- [ ] **Step 4: 提交**

```bash
git add web/server/database/schema/sqlite.ts web/server/database/schema/pg.ts web/server/database/schema/index.ts
git commit -m "feat(db): add simulation_snapshots and agent_conversations tables"
```

---

## Task 5: Web Server API (5 个路由)

**Files:**
- Create: `web/server/api/timemachine/[simId]/snapshots.get.ts`
- Create: `web/server/api/timemachine/[simId]/snapshots/[round].get.ts`
- Create: `web/server/api/timemachine/[simId]/chat.post.ts`
- Create: `web/server/api/timemachine/[simId]/roundtable.post.ts`
- Create: `web/server/api/timemachine/[simId]/replay.get.ts`

- [ ] **Step 1: 快照列表路由**

```typescript
// web/server/api/timemachine/[simId]/snapshots.get.ts
import { eq, and } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { simulations, simulationSnapshots } from '~~/server/database/schema'
import { success, error, ErrorCodes } from '~~/server/utils/response'

export default defineEventHandler(async (event) => {
  const simId = getRouterParam(event, 'simId')!
  const { enterpriseId } = event.context.user!
  const db = useDB()
  const config = useRuntimeConfig()

  const sims = await db.select().from(simulations)
    .where(and(eq(simulations.id, simId), eq(simulations.enterpriseId, enterpriseId)))
    .limit(1)

  if (sims.length === 0) return error(ErrorCodes.NOT_FOUND, '仿真不存在')
  const sim = sims[0]

  if (sim.status !== 'completed') return error(ErrorCodes.VALIDATION_ERROR, '仿真未完成')

  // Check if snapshots already cached
  const cached = await db.select().from(simulationSnapshots)
    .where(and(
      eq(simulationSnapshots.simulationId, simId),
      eq(simulationSnapshots.enterpriseId, enterpriseId),
    ))
    .orderBy(simulationSnapshots.roundNumber)

  if (cached.length > 0) {
    return success(cached.map(s => ({
      ...s,
      snapshotData: JSON.parse(s.snapshotData),
    })))
  }

  // Extract from engine
  let simConfig
  try {
    simConfig = JSON.parse(sim.config)
  } catch {
    return error(ErrorCodes.SERVER_ERROR, '仿真配置数据损坏')
  }

  const dbPath = simConfig.db_path || simConfig.dbPath
  if (!dbPath) return error(ErrorCodes.SERVER_ERROR, '仿真数据库路径不可用')

  try {
    const result = await $fetch<any>(`${config.engineUrl}/engine/timemachine/snapshots`, {
      method: 'POST',
      headers: { 'X-Internal-Key': config.internalApiKey, 'Content-Type': 'application/json' },
      body: { db_path: dbPath, num_steps: sim.timeSteps || 5 },
    })

    // Cache snapshots
    const { generateId, now } = await import('~~/server/utils/id')
    for (const snap of (result.snapshots || [])) {
      await db.insert(simulationSnapshots).values({
        id: generateId(),
        simulationId: simId,
        enterpriseId,
        roundNumber: snap.round_number,
        snapshotData: JSON.stringify(snap),
        createdAt: now(),
      })
    }

    return success(result.snapshots || [])
  } catch (e: any) {
    return error(ErrorCodes.ENGINE_DISPATCH_FAILED, '快照提取失败: ' + (e.message || ''))
  }
})
```

- [ ] **Step 2: 特定轮次快照路由**

```typescript
// web/server/api/timemachine/[simId]/snapshots/[round].get.ts
import { eq, and } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { simulations, simulationSnapshots } from '~~/server/database/schema'
import { success, error, ErrorCodes } from '~~/server/utils/response'

export default defineEventHandler(async (event) => {
  const simId = getRouterParam(event, 'simId')!
  const roundStr = getRouterParam(event, 'round')!
  const roundNumber = parseInt(roundStr, 10)
  const { enterpriseId } = event.context.user!
  const db = useDB()
  const config = useRuntimeConfig()

  if (isNaN(roundNumber) || roundNumber < 1) {
    return error(ErrorCodes.VALIDATION_ERROR, '轮次参数无效')
  }

  const sims = await db.select().from(simulations)
    .where(and(eq(simulations.id, simId), eq(simulations.enterpriseId, enterpriseId)))
    .limit(1)

  if (sims.length === 0) return error(ErrorCodes.NOT_FOUND, '仿真不存在')
  const sim = sims[0]

  // Check cache
  const cached = await db.select().from(simulationSnapshots)
    .where(and(
      eq(simulationSnapshots.simulationId, simId),
      eq(simulationSnapshots.enterpriseId, enterpriseId),
      eq(simulationSnapshots.roundNumber, roundNumber),
    ))
    .limit(1)

  if (cached.length > 0) {
    try {
      return success(JSON.parse(cached[0].snapshotData))
    } catch {
      // Fall through to re-extract
    }
  }

  let simConfig
  try {
    simConfig = JSON.parse(sim.config)
  } catch {
    return error(ErrorCodes.SERVER_ERROR, '仿真配置数据损坏')
  }

  const dbPath = simConfig.db_path || simConfig.dbPath
  if (!dbPath) return error(ErrorCodes.SERVER_ERROR, '仿真数据库路径不可用')

  try {
    const result = await $fetch<any>(`${config.engineUrl}/engine/timemachine/snapshots`, {
      method: 'POST',
      headers: { 'X-Internal-Key': config.internalApiKey, 'Content-Type': 'application/json' },
      body: { db_path: dbPath, num_steps: sim.timeSteps || 5, round_number: roundNumber },
    })

    return success(result.snapshot || null)
  } catch (e: any) {
    return error(ErrorCodes.ENGINE_DISPATCH_FAILED, '快照提取失败: ' + (e.message || ''))
  }
})
```

- [ ] **Step 3: Agent 对话路由**

```typescript
// web/server/api/timemachine/[simId]/chat.post.ts
import { eq, and } from 'drizzle-orm'
import { z } from 'zod'
import { useDB } from '~~/server/database'
import { simulations, agentConversations } from '~~/server/database/schema'
import { success, error, ErrorCodes } from '~~/server/utils/response'

const schema = z.object({
  agentId: z.number().int().min(0),
  roundContext: z.number().int().min(1),
  message: z.string().min(1).max(2000),
  conversationId: z.string().optional(),
  history: z.array(z.object({
    role: z.string(),
    content: z.string(),
    agent_id: z.number().optional(),
    agent_name: z.string().optional(),
  })).optional(),
})

export default defineEventHandler(async (event) => {
  const simId = getRouterParam(event, 'simId')!
  const { enterpriseId } = event.context.user!
  const db = useDB()
  const config = useRuntimeConfig()

  const body = await readBody(event)
  const parsed = schema.safeParse(body)
  if (!parsed.success) return error(ErrorCodes.VALIDATION_ERROR, '参数错误')

  const sims = await db.select().from(simulations)
    .where(and(eq(simulations.id, simId), eq(simulations.enterpriseId, enterpriseId)))
    .limit(1)

  if (sims.length === 0) return error(ErrorCodes.NOT_FOUND, '仿真不存在')
  const sim = sims[0]

  let simConfig
  try {
    simConfig = JSON.parse(sim.config)
  } catch {
    return error(ErrorCodes.SERVER_ERROR, '仿真配置数据损坏')
  }

  const dbPath = simConfig.db_path || simConfig.dbPath
  if (!dbPath) return error(ErrorCodes.SERVER_ERROR, '仿真数据库路径不可用')

  try {
    const result = await $fetch<any>(`${config.engineUrl}/engine/timemachine/chat`, {
      method: 'POST',
      headers: { 'X-Internal-Key': config.internalApiKey, 'Content-Type': 'application/json' },
      body: {
        db_path: dbPath,
        agent_id: parsed.data.agentId,
        round_context: parsed.data.roundContext,
        message: parsed.data.message,
        history: parsed.data.history,
      },
    })

    // Save conversation
    const { generateId, now } = await import('~~/server/utils/id')
    const convId = parsed.data.conversationId || generateId()
    const newMessages = [
      ...(parsed.data.history || []),
      { role: 'user', content: parsed.data.message },
      { role: 'agent', content: result.response, agent_id: result.agent_id, agent_name: result.agent_name },
    ]

    // Upsert conversation record
    const existing = await db.select().from(agentConversations)
      .where(eq(agentConversations.id, convId))
      .limit(1)

    if (existing.length > 0) {
      await db.update(agentConversations).set({
        messages: JSON.stringify(newMessages),
      }).where(eq(agentConversations.id, convId))
    } else {
      await db.insert(agentConversations).values({
        id: convId,
        simulationId: simId,
        enterpriseId,
        roundContext: parsed.data.roundContext,
        conversationType: 'chat',
        participants: JSON.stringify([parsed.data.agentId]),
        messages: JSON.stringify(newMessages),
        createdAt: now(),
      })
    }

    return success({ ...result, conversationId: convId })
  } catch (e: any) {
    return error(ErrorCodes.ENGINE_DISPATCH_FAILED, '对话失败: ' + (e.message || ''))
  }
})
```

- [ ] **Step 4: 圆桌会议路由**

```typescript
// web/server/api/timemachine/[simId]/roundtable.post.ts
import { eq, and } from 'drizzle-orm'
import { z } from 'zod'
import { useDB } from '~~/server/database'
import { simulations, agentConversations } from '~~/server/database/schema'
import { success, error, ErrorCodes } from '~~/server/utils/response'

const schema = z.object({
  agentIds: z.array(z.number().int().min(0)).min(2).max(8),
  roundContext: z.number().int().min(1),
  topic: z.string().min(1).max(500),
  numRounds: z.number().int().min(1).max(5).default(3),
})

export default defineEventHandler(async (event) => {
  const simId = getRouterParam(event, 'simId')!
  const { enterpriseId } = event.context.user!
  const db = useDB()
  const config = useRuntimeConfig()

  const body = await readBody(event)
  const parsed = schema.safeParse(body)
  if (!parsed.success) return error(ErrorCodes.VALIDATION_ERROR, '参数错误')

  const sims = await db.select().from(simulations)
    .where(and(eq(simulations.id, simId), eq(simulations.enterpriseId, enterpriseId)))
    .limit(1)

  if (sims.length === 0) return error(ErrorCodes.NOT_FOUND, '仿真不存在')
  const sim = sims[0]

  let simConfig
  try {
    simConfig = JSON.parse(sim.config)
  } catch {
    return error(ErrorCodes.SERVER_ERROR, '仿真配置数据损坏')
  }

  const dbPath = simConfig.db_path || simConfig.dbPath
  if (!dbPath) return error(ErrorCodes.SERVER_ERROR, '仿真数据库路径不可用')

  try {
    const result = await $fetch<any>(`${config.engineUrl}/engine/timemachine/roundtable`, {
      method: 'POST',
      headers: { 'X-Internal-Key': config.internalApiKey, 'Content-Type': 'application/json' },
      body: {
        db_path: dbPath,
        agent_ids: parsed.data.agentIds,
        round_context: parsed.data.roundContext,
        topic: parsed.data.topic,
        num_rounds: parsed.data.numRounds,
      },
    })

    // Save conversation
    const { generateId, now } = await import('~~/server/utils/id')
    await db.insert(agentConversations).values({
      id: generateId(),
      simulationId: simId,
      enterpriseId,
      roundContext: parsed.data.roundContext,
      conversationType: 'roundtable',
      participants: JSON.stringify(parsed.data.agentIds),
      messages: JSON.stringify(result.messages || []),
      topic: parsed.data.topic,
      createdAt: now(),
    })

    return success(result)
  } catch (e: any) {
    return error(ErrorCodes.ENGINE_DISPATCH_FAILED, '圆桌会议失败: ' + (e.message || ''))
  }
})
```

- [ ] **Step 5: 重放数据路由**

```typescript
// web/server/api/timemachine/[simId]/replay.get.ts
import { eq, and, asc } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { simulations, simulationSnapshots } from '~~/server/database/schema'
import { success, error, ErrorCodes } from '~~/server/utils/response'

export default defineEventHandler(async (event) => {
  const simId = getRouterParam(event, 'simId')!
  const { enterpriseId } = event.context.user!
  const db = useDB()

  const sims = await db.select().from(simulations)
    .where(and(eq(simulations.id, simId), eq(simulations.enterpriseId, enterpriseId)))
    .limit(1)

  if (sims.length === 0) return error(ErrorCodes.NOT_FOUND, '仿真不存在')
  const sim = sims[0]

  const snapshots = await db.select().from(simulationSnapshots)
    .where(and(
      eq(simulationSnapshots.simulationId, simId),
      eq(simulationSnapshots.enterpriseId, enterpriseId),
    ))
    .orderBy(asc(simulationSnapshots.roundNumber))

  const replayData = snapshots.map(s => {
    let data
    try {
      data = JSON.parse(s.snapshotData)
    } catch {
      data = {}
    }
    return {
      round: s.roundNumber,
      ...data,
    }
  })

  return success({
    simulationId: simId,
    totalRounds: sim.timeSteps || replayData.length,
    platform: sim.platform,
    agentCount: sim.agentCount,
    rounds: replayData,
  })
})
```

- [ ] **Step 6: 提交**

```bash
git add web/server/api/timemachine/
git commit -m "feat(api): add time machine server API routes (snapshots, chat, roundtable, replay)"
```

---

## Task 6: Frontend Store

**Files:**
- Create: `web/app/stores/timemachine.ts`

- [ ] **Step 1: 创建 Pinia Store**

```typescript
// web/app/stores/timemachine.ts
import { defineStore } from 'pinia'

export interface SnapshotSummary {
  round_number: number
  metrics: {
    total_actions: number
    total_posts_this_round: number
    action_distribution: Record<string, number>
  }
  agent_summaries: {
    agent_id: number
    user_name: string
    action_count: number
    recent_actions: string[]
  }[]
  posts: any[]
}

export const useTimeMachineStore = defineStore('timeMachine', {
  state: () => ({
    snapshots: [] as SnapshotSummary[],
    currentRound: 1,
    currentSnapshot: null as SnapshotSummary | null,
    chatMessages: [] as any[],
    conversationId: null as string | null,
    roundtableMessages: [] as any[],
    replayData: null as any,
    loading: false,
    chatLoading: false,
  }),

  actions: {
    async fetchSnapshots(simId: string) {
      this.loading = true
      try {
        const { $api } = useApi()
        const res = await $api<any>(`/api/timemachine/${simId}/snapshots`)
        if (res.code === 0) {
          this.snapshots = res.data || []
          if (this.snapshots.length > 0) {
            this.currentRound = 1
            this.currentSnapshot = this.snapshots[0]
          }
        }
        return res
      } finally {
        this.loading = false
      }
    },

    async fetchRoundSnapshot(simId: string, round: number) {
      this.loading = true
      try {
        const { $api } = useApi()
        const res = await $api<any>(`/api/timemachine/${simId}/snapshots/${round}`)
        if (res.code === 0) {
          this.currentRound = round
          this.currentSnapshot = res.data
        }
        return res
      } finally {
        this.loading = false
      }
    },

    async sendChat(simId: string, agentId: number, roundContext: number, message: string) {
      this.chatLoading = true
      try {
        const { $api } = useApi()
        const res = await $api<any>(`/api/timemachine/${simId}/chat`, {
          method: 'POST',
          body: {
            agentId,
            roundContext,
            message,
            conversationId: this.conversationId,
            history: this.chatMessages,
          },
        })
        if (res.code === 0) {
          this.conversationId = res.data.conversationId
          this.chatMessages.push(
            { role: 'user', content: message },
            { role: 'agent', content: res.data.response, agent_id: res.data.agent_id, agent_name: res.data.agent_name },
          )
        }
        return res
      } finally {
        this.chatLoading = false
      }
    },

    async startRoundtable(simId: string, agentIds: number[], roundContext: number, topic: string, numRounds: number = 3) {
      this.chatLoading = true
      try {
        const { $api } = useApi()
        const res = await $api<any>(`/api/timemachine/${simId}/roundtable`, {
          method: 'POST',
          body: { agentIds, roundContext, topic, numRounds },
        })
        if (res.code === 0) {
          this.roundtableMessages = res.data.messages || []
        }
        return res
      } finally {
        this.chatLoading = false
      }
    },

    async fetchReplay(simId: string) {
      this.loading = true
      try {
        const { $api } = useApi()
        const res = await $api<any>(`/api/timemachine/${simId}/replay`)
        if (res.code === 0) {
          this.replayData = res.data
        }
        return res
      } finally {
        this.loading = false
      }
    },

    clearChat() {
      this.chatMessages = []
      this.conversationId = null
    },

    setRound(round: number) {
      this.currentRound = round
      const snap = this.snapshots.find(s => s.round_number === round)
      if (snap) this.currentSnapshot = snap
    },
  },
})
```

- [ ] **Step 2: 提交**

```bash
git add web/app/stores/timemachine.ts
git commit -m "feat(store): add time machine Pinia store"
```

---

## Task 7: TimelineSlider 组件

**Files:**
- Create: `web/app/components/TimelineSlider.vue`

- [ ] **Step 1: 创建时间轴滑块组件**

```vue
<!-- web/app/components/TimelineSlider.vue -->
<template>
  <n-card size="small">
    <div style="display: flex; align-items: center; gap: 16px">
      <n-text strong style="white-space: nowrap">轮次 {{ modelValue }} / {{ max }}</n-text>
      <n-slider
        :value="modelValue"
        :min="1"
        :max="max"
        :step="1"
        :marks="sliderMarks"
        style="flex: 1"
        @update:value="$emit('update:modelValue', $event)"
      />
    </div>
  </n-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  modelValue: number
  max: number
}>()

defineEmits<{
  'update:modelValue': [value: number]
}>()

const sliderMarks = computed(() => {
  const marks: Record<number, string> = {}
  if (props.max <= 20) {
    for (let i = 1; i <= props.max; i++) marks[i] = String(i)
  } else {
    const step = Math.ceil(props.max / 10)
    for (let i = 1; i <= props.max; i += step) marks[i] = String(i)
    marks[props.max] = String(props.max)
  }
  return marks
})
</script>
```

- [ ] **Step 2: 提交**

```bash
git add web/app/components/TimelineSlider.vue
git commit -m "feat(ui): add timeline slider component"
```

---

## Task 8: SnapshotViewer + AgentChatPanel + ReplayPlayer 组件

**Files:**
- Create: `web/app/components/SnapshotViewer.vue`
- Create: `web/app/components/AgentChatPanel.vue`
- Create: `web/app/components/ReplayPlayer.vue`

- [ ] **Step 1: 创建快照查看组件**

```vue
<!-- web/app/components/SnapshotViewer.vue -->
<template>
  <n-grid :cols="2" :x-gap="16" :y-gap="16" v-if="snapshot">
    <n-gi>
      <n-card title="轮次指标" size="small">
        <n-space vertical>
          <n-text>总行为: {{ snapshot.metrics.total_actions }}</n-text>
          <n-text>新帖子: {{ snapshot.metrics.total_posts_this_round }}</n-text>
        </n-space>
        <div ref="actionChartRef" style="height: 200px; margin-top: 12px" />
      </n-card>
    </n-gi>
    <n-gi>
      <n-card title="活跃 Agent" size="small">
        <n-list :show-divider="false" style="max-height: 280px; overflow-y: auto">
          <n-list-item v-for="a in snapshot.agent_summaries" :key="a.agent_id">
            <n-space justify="space-between" align="center" style="width: 100%">
              <n-button
                text
                type="primary"
                @click="$emit('selectAgent', a.agent_id, a.user_name)"
              >
                {{ a.user_name }}
              </n-button>
              <n-space>
                <n-tag size="tiny" type="info">{{ a.action_count }} 次行为</n-tag>
              </n-space>
            </n-space>
          </n-list-item>
        </n-list>
      </n-card>
    </n-gi>
    <n-gi :span="2" v-if="snapshot.posts.length">
      <n-card title="本轮帖子" size="small">
        <n-list :show-divider="false" style="max-height: 300px; overflow-y: auto">
          <n-list-item v-for="(p, idx) in snapshot.posts.slice(0, 20)" :key="idx">
            <n-text depth="3" style="font-size: 12px">Agent {{ p.user_id }}:</n-text>
            <n-text>{{ p.content }}</n-text>
          </n-list-item>
        </n-list>
      </n-card>
    </n-gi>
  </n-grid>
</template>

<script setup lang="ts">
import { ref, watch, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent } from 'echarts/components'

echarts.use([CanvasRenderer, PieChart, TooltipComponent, LegendComponent])

const props = defineProps<{ snapshot: any }>()
defineEmits<{ selectAgent: [agentId: number, agentName: string] }>()

const actionChartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

function renderChart() {
  if (!actionChartRef.value || !props.snapshot) return
  if (!chart) {
    chart = echarts.init(actionChartRef.value)
  }
  const dist = props.snapshot.metrics.action_distribution || {}
  chart.setOption({
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie', radius: ['35%', '65%'],
      data: Object.entries(dist).map(([name, value]) => ({ name, value })),
    }],
  }, true)
}

watch(() => props.snapshot, () => nextTick(renderChart), { immediate: true, deep: true })
onUnmounted(() => { if (chart) { chart.dispose(); chart = null } })
</script>
```

- [ ] **Step 2: 创建 Agent 对话面板**

```vue
<!-- web/app/components/AgentChatPanel.vue -->
<template>
  <n-drawer :show="!!agentId" :width="420" placement="right" @update:show="$emit('close')">
    <n-drawer-content :title="`与 ${agentName} 对话 (第${roundContext}轮)`" closable>
      <div class="chat-messages" ref="messagesRef">
        <div
          v-for="(msg, idx) in messages"
          :key="idx"
          :class="['chat-bubble', msg.role === 'user' ? 'chat-user' : 'chat-agent']"
        >
          <n-text depth="3" style="font-size: 11px">{{ msg.role === 'user' ? '你' : msg.agent_name || agentName }}</n-text>
          <n-text>{{ msg.content }}</n-text>
        </div>
        <div v-if="loading" style="text-align: center; padding: 12px">
          <n-spin size="small" />
        </div>
      </div>

      <template #footer>
        <n-input-group>
          <n-input
            v-model:value="inputText"
            placeholder="输入消息..."
            :disabled="loading"
            @keydown.enter.prevent="send"
          />
          <n-button type="primary" :loading="loading" :disabled="!inputText.trim()" @click="send">
            发送
          </n-button>
        </n-input-group>
      </template>
    </n-drawer-content>
  </n-drawer>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'

const props = defineProps<{
  agentId: number | null
  agentName: string
  roundContext: number
  messages: any[]
  loading: boolean
}>()

const emit = defineEmits<{
  close: []
  send: [message: string]
}>()

const inputText = ref('')
const messagesRef = ref<HTMLElement>()

function send() {
  const text = inputText.value.trim()
  if (!text) return
  emit('send', text)
  inputText.value = ''
}

watch(() => props.messages.length, () => {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
})
</script>

<style scoped>
.chat-messages {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-bottom: 12px;
}

.chat-bubble {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 14px;
  border-radius: 12px;
  max-width: 85%;
}

.chat-user {
  align-self: flex-end;
  background: #e8f4fd;
}

.chat-agent {
  align-self: flex-start;
  background: #f5f5f5;
}
</style>
```

- [ ] **Step 3: 创建重放播放器**

```vue
<!-- web/app/components/ReplayPlayer.vue -->
<template>
  <n-card title="情境重放" size="small" v-if="data">
    <template #header-extra>
      <n-space>
        <n-button size="tiny" @click="togglePlay">
          {{ playing ? '暂停' : '播放' }}
        </n-button>
        <n-select
          v-model:value="speed"
          size="tiny"
          style="width: 80px"
          :options="speedOptions"
        />
      </n-space>
    </template>

    <n-text depth="3" style="font-size: 12px">
      轮次 {{ currentRound }} / {{ data.totalRounds }} | {{ data.platform }} | {{ data.agentCount }} Agents
    </n-text>

    <n-progress
      :percentage="(currentRound / data.totalRounds) * 100"
      :show-indicator="false"
      :height="4"
      style="margin: 8px 0"
    />

    <div v-if="currentRoundData" style="max-height: 300px; overflow-y: auto">
      <n-list :show-divider="false">
        <n-list-item v-for="(p, idx) in (currentRoundData.posts || []).slice(0, 10)" :key="idx">
          <n-text depth="3" style="font-size: 12px">Agent {{ p.user_id }}:</n-text>
          <n-text>{{ p.content }}</n-text>
        </n-list-item>
      </n-list>
      <n-empty v-if="!currentRoundData.posts?.length" description="本轮无新帖子" size="small" />
    </div>
  </n-card>
</template>

<script setup lang="ts">
import { ref, computed, onUnmounted, watch } from 'vue'

const props = defineProps<{ data: any }>()
const emit = defineEmits<{ roundChange: [round: number] }>()

const currentRound = ref(1)
const playing = ref(false)
const speed = ref(1)
let timer: ReturnType<typeof setInterval> | null = null

const speedOptions = [
  { label: '0.5x', value: 0.5 },
  { label: '1x', value: 1 },
  { label: '2x', value: 2 },
  { label: '4x', value: 4 },
]

const currentRoundData = computed(() => {
  if (!props.data?.rounds) return null
  return props.data.rounds.find((r: any) => r.round === currentRound.value || r.round_number === currentRound.value)
})

function togglePlay() {
  if (playing.value) {
    stopPlay()
  } else {
    startPlay()
  }
}

function startPlay() {
  playing.value = true
  timer = setInterval(() => {
    if (currentRound.value >= (props.data?.totalRounds || 1)) {
      stopPlay()
      return
    }
    currentRound.value++
    emit('roundChange', currentRound.value)
  }, 2000 / speed.value)
}

function stopPlay() {
  playing.value = false
  if (timer) { clearInterval(timer); timer = null }
}

watch(speed, () => {
  if (playing.value) {
    stopPlay()
    startPlay()
  }
})

onUnmounted(stopPlay)
</script>
```

- [ ] **Step 4: 提交**

```bash
git add web/app/components/SnapshotViewer.vue web/app/components/AgentChatPanel.vue web/app/components/ReplayPlayer.vue
git commit -m "feat(ui): add snapshot viewer, agent chat panel, and replay player components"
```

---

## Task 9: 时间机器主页面

**Files:**
- Create: `web/app/pages/simulations/[id]/timemachine.vue`

- [ ] **Step 1: 创建时间机器页面**

```vue
<!-- web/app/pages/simulations/[id]/timemachine.vue -->
<template>
  <div>
    <CommonPageHeader title="时间机器" :subtitle="simName">
      <template #actions>
        <n-space>
          <n-button @click="showRoundtable = true" :disabled="!store.snapshots.length">圆桌会议</n-button>
          <n-button @click="loadReplay" :disabled="!store.snapshots.length">情境重放</n-button>
          <n-button @click="router.push(`/simulations/${simId}`)">返回仿真</n-button>
        </n-space>
      </template>
    </CommonPageHeader>

    <n-spin :show="store.loading">
      <n-empty v-if="!store.snapshots.length && !store.loading" description="仿真未完成或快照数据不可用">
        <template #extra>
          <n-button @click="router.push(`/simulations/${simId}`)">返回仿真详情</n-button>
        </template>
      </n-empty>

      <div v-if="store.snapshots.length" style="display: flex; flex-direction: column; gap: 16px">
        <TimelineSlider v-model="store.currentRound" :max="totalRounds" @update:model-value="onRoundChange" />

        <SnapshotViewer
          :snapshot="store.currentSnapshot"
          @select-agent="openChat"
        />

        <ReplayPlayer
          v-if="store.replayData"
          :data="store.replayData"
          @round-change="onRoundChange"
        />
      </div>
    </n-spin>

    <AgentChatPanel
      :agent-id="chatAgentId"
      :agent-name="chatAgentName"
      :round-context="store.currentRound"
      :messages="store.chatMessages"
      :loading="store.chatLoading"
      @close="closeChat"
      @send="handleChatSend"
    />

    <n-modal v-model:show="showRoundtable" title="发起圆桌会议" preset="card" style="width: 500px">
      <n-form>
        <n-form-item label="讨论话题">
          <n-input v-model:value="roundtableForm.topic" placeholder="输入讨论话题" />
        </n-form-item>
        <n-form-item label="参与 Agent (点击选择)">
          <n-select
            v-model:value="roundtableForm.agentIds"
            multiple
            :options="agentOptions"
            placeholder="选择 2-8 个 Agent"
          />
        </n-form-item>
        <n-form-item label="讨论轮数">
          <n-input-number v-model:value="roundtableForm.numRounds" :min="1" :max="5" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-button type="primary" :loading="store.chatLoading" @click="startRoundtable">开始讨论</n-button>
      </template>
    </n-modal>

    <n-modal v-model:show="showRoundtableResult" title="圆桌会议记录" preset="card" style="width: 600px">
      <div style="max-height: 500px; overflow-y: auto">
        <div
          v-for="(msg, idx) in store.roundtableMessages"
          :key="idx"
          style="margin-bottom: 12px; padding: 10px; background: #f9f9f9; border-radius: 8px"
        >
          <n-text strong>{{ msg.agent_name }}</n-text>
          <n-text style="display: block; margin-top: 4px">{{ msg.content }}</n-text>
        </div>
      </div>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useTimeMachineStore } from '~/stores/timemachine'
import { useSimulationsStore } from '~/stores/simulations'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const store = useTimeMachineStore()
const simStore = useSimulationsStore()

const simId = route.params.id as string

const chatAgentId = ref<number | null>(null)
const chatAgentName = ref('')
const showRoundtable = ref(false)
const showRoundtableResult = ref(false)
const roundtableForm = ref({ topic: '', agentIds: [] as number[], numRounds: 3 })

const simName = computed(() => simStore.currentSimulation?.name || '仿真')
const totalRounds = computed(() => store.snapshots.length || 1)

const agentOptions = computed(() => {
  if (!store.currentSnapshot?.agent_summaries) return []
  return store.currentSnapshot.agent_summaries.map((a: any) => ({
    label: a.user_name,
    value: a.agent_id,
  }))
})

function onRoundChange(round: number) {
  store.setRound(round)
}

function openChat(agentId: number, agentName: string) {
  store.clearChat()
  chatAgentId.value = agentId
  chatAgentName.value = agentName
}

function closeChat() {
  chatAgentId.value = null
}

async function handleChatSend(text: string) {
  if (!chatAgentId.value) return
  const res = await store.sendChat(simId, chatAgentId.value, store.currentRound, text)
  if (res.code !== 0) message.error(res.message)
}

async function startRoundtable() {
  if (!roundtableForm.value.topic) return message.warning('请输入讨论话题')
  if (roundtableForm.value.agentIds.length < 2) return message.warning('至少选择 2 个 Agent')

  const res = await store.startRoundtable(
    simId,
    roundtableForm.value.agentIds,
    store.currentRound,
    roundtableForm.value.topic,
    roundtableForm.value.numRounds,
  )
  if (res.code === 0) {
    showRoundtable.value = false
    showRoundtableResult.value = true
  } else {
    message.error(res.message)
  }
}

async function loadReplay() {
  const res = await store.fetchReplay(simId)
  if (res.code !== 0) message.error(res.message)
}

onMounted(async () => {
  await simStore.fetchOne(simId)
  await store.fetchSnapshots(simId)
})
</script>
```

- [ ] **Step 2: 提交**

```bash
git add web/app/pages/simulations/[id]/timemachine.vue
git commit -m "feat(ui): add time machine page"
```

---

## Task 10: 仿真详情页添加入口

**Files:**
- Modify: `web/app/pages/simulations/[id].vue`

- [ ] **Step 1: 在仿真详情页添加「时间机器」按钮**

在 `NSpace` 中已完成的仿真显示区域，在「生成深度分析报告」按钮之后添加：

```vue
<NButton v-if="sim?.status === 'completed'" type="info" @click="router.push(`/simulations/${id}/timemachine`)">时间机器</NButton>
```

- [ ] **Step 2: 提交**

```bash
git add web/app/pages/simulations/[id].vue
git commit -m "feat(ui): add time machine entry button on simulation detail page"
```

---

## Task 11: 最终审查

- [ ] **Step 1: 代码审查**

检查所有新文件的：
1. 安全性：enterpriseId 过滤、Zod 验证
2. 一致性：与现有模式匹配（success/error 响应、store 模式）
3. JSON.parse 都有 try/catch 保护
4. 导入路径正确
5. 数据库表在 sqlite.ts 和 pg.ts 中一致
6. Engine API 端点有 verify_internal_key 保护
