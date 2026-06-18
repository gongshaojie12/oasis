# 工作区级大模型 Key 配置 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让用户在「设置」页为当前工作区配置大模型 provider + API Key,聊天/模拟自动用该配置跑真实模型。

**Architecture:** 新增独立的 `workspace_model_config` 表 + 双 store 实现(SQLite/PG/InMemory)+ 独立路由(`model_config.py`);新增 OpenAI 兼容 ModelCall 适配器;打通 `resolve_effective_model` 的工作区默认级(替代 `auth.py` 写死的 `None`);前端在 `SettingsView` 加配置卡片并修掉写死的 stub。

**Tech Stack:** Python 3 / FastAPI / Pydantic v2 / sqlite3 / camel-ai(ModelFactory)/ React 18 / TypeScript / Vite / vitest / pytest。

## Global Constraints

- 文件头版权注释:每个新 `.py` 文件首行 `# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========`,前端 `.ts/.tsx` 首行 `// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========`。
- Python 环境统一用 `D:/software/conda_data/envs/oasis/python.exe`(base 没装 camel-ai)。
- Store DSN 分发模式照搬 `wanxiang/api/api_keys.py:74` `make_*_store`:`None`→InMemory;无 scheme / `sqlite://`→SQLite;`postgresql://`→PG。
- 完整 API Key **永不**出现在任何对外 JSON 响应里,只存数据库 + 实际发起 LLM 调用时使用。GET 一律返回脱敏值。
- 权限复用 `wanxiang/api/routes/workspaces.py` 的 helper:读用 `_require_member`,写用 `_require_admin_or_owner`。
- 路由经 `app.py` 的 `try/except include_router` 块挂载,prefix=`/v1`。
- provider 取值集合(预设 id):`stub` / `deepseek` / `openai` / `qwen` / `custom`。
- 测试目录 `test/wanxiang/`,pytest 风格。运行单测:`D:/software/conda_data/envs/oasis/python.exe -m pytest <path> -v`。

---

### Task 1: Provider 预设表 + 模型解析辅助(纯函数,无 IO)

**Files:**
- Create: `wanxiang/api/model_presets.py`
- Test: `test/wanxiang/test_model_presets_data.py`

**Interfaces:**
- Produces:
  - `MODEL_PRESETS: list[dict]` — 每项含 `id,label,base_url,default_model,needs_key,allow_custom_base_url`
  - `get_preset(provider_id: str) -> dict | None`
  - `mask_key(key: str | None) -> str | None` — 返回如 `sk-…1234`(尾 4 位),`None`/空 → `None`

- [ ] **Step 1: 写失败测试**

```python
# test/wanxiang/test_model_presets_data.py
from wanxiang.api.model_presets import MODEL_PRESETS, get_preset, mask_key


def test_presets_have_required_ids():
    ids = {p["id"] for p in MODEL_PRESETS}
    assert {"stub", "deepseek", "openai", "qwen", "custom"} <= ids


def test_each_preset_has_all_fields():
    for p in MODEL_PRESETS:
        assert set(p) == {"id", "label", "base_url", "default_model",
                          "needs_key", "allow_custom_base_url"}


def test_get_preset_found_and_missing():
    assert get_preset("deepseek")["default_model"] == "deepseek-chat"
    assert get_preset("nope") is None


def test_custom_allows_base_url_and_needs_key():
    c = get_preset("custom")
    assert c["allow_custom_base_url"] is True
    assert c["needs_key"] is True
    assert c["base_url"] is None


def test_stub_needs_no_key():
    assert get_preset("stub")["needs_key"] is False


def test_mask_key():
    assert mask_key("sk-abcdef1234") == "sk-…1234"
    assert mask_key("") is None
    assert mask_key(None) is None
    assert mask_key("ab") == "…ab"
```

- [ ] **Step 2: 运行确认失败**

Run: `D:/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_model_presets_data.py -v`
Expected: FAIL — `ModuleNotFoundError: wanxiang.api.model_presets`

- [ ] **Step 3: 写实现**

```python
# wanxiang/api/model_presets.py
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""Provider 预设表(静态,不入库)+ key 脱敏辅助。

新增主流 provider = 往 MODEL_PRESETS 加一行,不碰核心代码。
"""
from __future__ import annotations

MODEL_PRESETS: list[dict] = [
    {"id": "deepseek", "label": "DeepSeek",
     "base_url": "https://api.deepseek.com/v1",
     "default_model": "deepseek-chat",
     "needs_key": True, "allow_custom_base_url": False},
    {"id": "openai", "label": "OpenAI",
     "base_url": "https://api.openai.com/v1",
     "default_model": "gpt-4o-mini",
     "needs_key": True, "allow_custom_base_url": False},
    {"id": "qwen", "label": "通义千问",
     "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
     "default_model": "qwen-plus",
     "needs_key": True, "allow_custom_base_url": False},
    {"id": "custom", "label": "自定义 (OpenAI 兼容)",
     "base_url": None, "default_model": None,
     "needs_key": True, "allow_custom_base_url": True},
    {"id": "stub", "label": "测试桩 (无需 key)",
     "base_url": None, "default_model": None,
     "needs_key": False, "allow_custom_base_url": False},
]


def get_preset(provider_id: str) -> dict | None:
    return next((p for p in MODEL_PRESETS if p["id"] == provider_id), None)


def mask_key(key: str | None) -> str | None:
    """脱敏:保留尾 4 位,其余以 … 代替。空/None → None。"""
    if not key:
        return None
    tail = key[-4:]
    return f"…{tail}" if len(key) <= 4 else f"{key[:3]}…{tail}"
```

- [ ] **Step 4: 运行确认通过**

Run: `D:/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_model_presets_data.py -v`
Expected: PASS(6 passed)

- [ ] **Step 5: 提交**

```bash
git add wanxiang/api/model_presets.py test/wanxiang/test_model_presets_data.py
git commit -m "feat(model-config): provider 预设表 + key 脱敏辅助

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2: 模型配置存储(record + InMemory + 工厂)

**Files:**
- Create: `wanxiang/api/model_config.py`
- Test: `test/wanxiang/test_model_config_store.py`

**Interfaces:**
- Consumes: 无
- Produces:
  - `@dataclass ModelConfigRecord(workspace_id, provider, api_key, base_url, model_name, updated_at, updated_by_user_id)`
  - `InMemoryModelConfigStore` 带方法 `get(workspace_id) -> ModelConfigRecord | None`、`upsert(rec: ModelConfigRecord) -> ModelConfigRecord`
  - `make_model_config_store(dsn: str | None, *, eager_init: bool = True)` — DSN 分发

- [ ] **Step 1: 写失败测试**

```python
# test/wanxiang/test_model_config_store.py
from datetime import datetime, timezone
from wanxiang.api.model_config import (ModelConfigRecord,
                                        make_model_config_store)


def _rec(ws="ws1", provider="deepseek", key="sk-abc1234",
         base_url=None, model_name=None, by="u1"):
    return ModelConfigRecord(
        workspace_id=ws, provider=provider, api_key=key,
        base_url=base_url, model_name=model_name,
        updated_at=datetime.now(timezone.utc), updated_by_user_id=by)


def test_get_missing_returns_none():
    store = make_model_config_store(None)
    assert store.get("nope") is None


def test_upsert_then_get():
    store = make_model_config_store(None)
    store.upsert(_rec())
    got = store.get("ws1")
    assert got.provider == "deepseek"
    assert got.api_key == "sk-abc1234"
    assert got.updated_by_user_id == "u1"


def test_upsert_overwrites_same_workspace():
    store = make_model_config_store(None)
    store.upsert(_rec(provider="deepseek", key="sk-old0001"))
    store.upsert(_rec(provider="openai", key="sk-new0002",
                      model_name="gpt-4o-mini"))
    got = store.get("ws1")
    assert got.provider == "openai"
    assert got.api_key == "sk-new0002"
    assert got.model_name == "gpt-4o-mini"
```

- [ ] **Step 2: 运行确认失败**

Run: `D:/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_model_config_store.py -v`
Expected: FAIL — `ModuleNotFoundError: wanxiang.api.model_config`

- [ ] **Step 3: 写实现**

```python
# wanxiang/api/model_config.py
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""每工作区一份大模型配置(provider + key + base_url + model_name)。

DSN 分发同 api_keys.py:None→InMemory;sqlite/路径→SQLite;postgresql→PG。
key 以明文存储(MVP,与 api_keys 一致),对外响应由路由层脱敏。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from threading import Lock
from urllib.parse import urlparse


@dataclass
class ModelConfigRecord:
    workspace_id: str
    provider: str
    api_key: str | None
    base_url: str | None
    model_name: str | None
    updated_at: datetime
    updated_by_user_id: str | None


class InMemoryModelConfigStore:
    def __init__(self):
        self._by_ws: dict[str, ModelConfigRecord] = {}
        self._lock = Lock()

    def get(self, workspace_id: str) -> ModelConfigRecord | None:
        return self._by_ws.get(workspace_id)

    def upsert(self, rec: ModelConfigRecord) -> ModelConfigRecord:
        with self._lock:
            self._by_ws[rec.workspace_id] = rec
        return rec


def make_model_config_store(dsn: str | None, *, eager_init: bool = True):
    if not dsn:
        return InMemoryModelConfigStore()
    parsed = urlparse(dsn)
    scheme = (parsed.scheme or "").lower()
    if len(scheme) == 1 and scheme.isalpha():
        scheme = ""
    if scheme in ("postgresql", "postgres"):
        from wanxiang.api.model_config_store_pg import PgModelConfigStore
        return PgModelConfigStore(dsn, eager_init=eager_init)
    if scheme == "sqlite":
        path = parsed.path or dsn[len("sqlite:"):]
        if path.startswith("/") and len(path) > 2 and path[2] == ":":
            path = path[1:]
        from wanxiang.api.model_config_store_sqlite import (
            SqliteModelConfigStore)
        return SqliteModelConfigStore(path)
    if not scheme:
        from wanxiang.api.model_config_store_sqlite import (
            SqliteModelConfigStore)
        return SqliteModelConfigStore(dsn)
    raise ValueError(f"unsupported model_config store DSN scheme: {scheme!r}")


__all__ = ["ModelConfigRecord", "InMemoryModelConfigStore",
           "make_model_config_store"]
```

- [ ] **Step 4: 运行确认通过**

Run: `D:/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_model_config_store.py -v`
Expected: PASS(3 passed)

- [ ] **Step 5: 提交**

```bash
git add wanxiang/api/model_config.py test/wanxiang/test_model_config_store.py
git commit -m "feat(model-config): ModelConfigRecord + InMemory store + 工厂

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 3: SQLite store 实现

**Files:**
- Create: `wanxiang/api/model_config_store_sqlite.py`
- Test: `test/wanxiang/test_model_config_store_sqlite.py`

**Interfaces:**
- Consumes: `ModelConfigRecord`(Task 2)
- Produces: `SqliteModelConfigStore(db_path)` 带 `get` / `upsert`(与 InMemory 同签名),被 `make_model_config_store` 的 sqlite 分支使用。

- [ ] **Step 1: 写失败测试**

```python
# test/wanxiang/test_model_config_store_sqlite.py
import os
import tempfile
from datetime import datetime, timezone
from wanxiang.api.model_config import ModelConfigRecord
from wanxiang.api.model_config_store_sqlite import SqliteModelConfigStore


def _store():
    d = tempfile.mkdtemp()
    return SqliteModelConfigStore(os.path.join(d, "mc.db"))


def _rec(**kw):
    base = dict(workspace_id="ws1", provider="deepseek",
               api_key="sk-abc1234", base_url=None, model_name=None,
               updated_at=datetime.now(timezone.utc),
               updated_by_user_id="u1")
    base.update(kw)
    return ModelConfigRecord(**base)


def test_get_missing_none():
    assert _store().get("ws1") is None


def test_upsert_get_roundtrip():
    s = _store()
    s.upsert(_rec(base_url="https://x/v1", model_name="deepseek-chat"))
    got = s.get("ws1")
    assert got.provider == "deepseek"
    assert got.base_url == "https://x/v1"
    assert got.model_name == "deepseek-chat"
    assert got.updated_by_user_id == "u1"


def test_upsert_overwrites():
    s = _store()
    s.upsert(_rec(api_key="sk-old0001"))
    s.upsert(_rec(provider="openai", api_key="sk-new0002"))
    got = s.get("ws1")
    assert got.provider == "openai"
    assert got.api_key == "sk-new0002"


def test_persists_across_instances():
    d = tempfile.mkdtemp()
    p = os.path.join(d, "mc.db")
    SqliteModelConfigStore(p).upsert(_rec())
    assert SqliteModelConfigStore(p).get("ws1").api_key == "sk-abc1234"
```

- [ ] **Step 2: 运行确认失败**

Run: `D:/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_model_config_store_sqlite.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 写实现**

```python
# wanxiang/api/model_config_store_sqlite.py
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""SqliteModelConfigStore —— 每工作区一行大模型配置。"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from threading import Lock

from wanxiang.api.model_config import ModelConfigRecord

_SCHEMA = """
CREATE TABLE IF NOT EXISTS workspace_model_config (
    workspace_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    api_key TEXT,
    base_url TEXT,
    model_name TEXT,
    updated_at TEXT NOT NULL,
    updated_by_user_id TEXT
);
"""


def _row_to_rec(row: sqlite3.Row) -> ModelConfigRecord:
    return ModelConfigRecord(
        workspace_id=row["workspace_id"],
        provider=row["provider"],
        api_key=row["api_key"],
        base_url=row["base_url"],
        model_name=row["model_name"],
        updated_at=datetime.fromisoformat(row["updated_at"]),
        updated_by_user_id=row["updated_by_user_id"],
    )


class SqliteModelConfigStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        parent = os.path.dirname(os.path.abspath(db_path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        self._lock = Lock()
        with self._connect() as conn:
            conn.executescript(_SCHEMA)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False,
                               isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def get(self, workspace_id: str) -> ModelConfigRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM workspace_model_config WHERE workspace_id = ?",
                (workspace_id,)).fetchone()
        return _row_to_rec(row) if row else None

    def upsert(self, rec: ModelConfigRecord) -> ModelConfigRecord:
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO workspace_model_config "
                "(workspace_id, provider, api_key, base_url, model_name, "
                " updated_at, updated_by_user_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(workspace_id) DO UPDATE SET "
                " provider=excluded.provider, api_key=excluded.api_key, "
                " base_url=excluded.base_url, model_name=excluded.model_name, "
                " updated_at=excluded.updated_at, "
                " updated_by_user_id=excluded.updated_by_user_id",
                (rec.workspace_id, rec.provider, rec.api_key, rec.base_url,
                 rec.model_name, rec.updated_at.isoformat(),
                 rec.updated_by_user_id))
        return rec
```

- [ ] **Step 4: 运行确认通过**

Run: `D:/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_model_config_store_sqlite.py -v`
Expected: PASS(4 passed)

- [ ] **Step 5: 提交**

```bash
git add wanxiang/api/model_config_store_sqlite.py test/wanxiang/test_model_config_store_sqlite.py
git commit -m "feat(model-config): SQLite store (upsert/get)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 4: PG store 实现

**Files:**
- Create: `wanxiang/api/model_config_store_pg.py`

**Interfaces:**
- Consumes: `ModelConfigRecord`(Task 2)
- Produces: `PgModelConfigStore(dsn, *, eager_init=True)` 带 `get` / `upsert`,被 `make_model_config_store` 的 pg 分支使用。

> 说明:PG 无单测(本地无 PG 实例;CI 的 PG 测试单独跑)。本任务以"代码与现有 `*_store_pg.py` 模式一致 + import 不报错"为验收。参照现有 `wanxiang/api/api_key_store_pg.py` 的连接/游标写法。

- [ ] **Step 1: 写实现**

```python
# wanxiang/api/model_config_store_pg.py
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""PgModelConfigStore —— PostgreSQL 后端,接口同 SQLite 版。"""
from __future__ import annotations

from datetime import datetime

from wanxiang.api.model_config import ModelConfigRecord

_SCHEMA = """
CREATE TABLE IF NOT EXISTS workspace_model_config (
    workspace_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    api_key TEXT,
    base_url TEXT,
    model_name TEXT,
    updated_at TEXT NOT NULL,
    updated_by_user_id TEXT
);
"""


class PgModelConfigStore:
    def __init__(self, dsn: str, *, eager_init: bool = True):
        self.dsn = dsn
        if eager_init:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(_SCHEMA)
                conn.commit()

    def _connect(self):
        import psycopg
        return psycopg.connect(self.dsn)

    def get(self, workspace_id: str) -> ModelConfigRecord | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT workspace_id, provider, api_key, base_url, "
                " model_name, updated_at, updated_by_user_id "
                "FROM workspace_model_config WHERE workspace_id = %s",
                (workspace_id,))
            row = cur.fetchone()
        if not row:
            return None
        return ModelConfigRecord(
            workspace_id=row[0], provider=row[1], api_key=row[2],
            base_url=row[3], model_name=row[4],
            updated_at=datetime.fromisoformat(row[5]),
            updated_by_user_id=row[6])

    def upsert(self, rec: ModelConfigRecord) -> ModelConfigRecord:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO workspace_model_config "
                    "(workspace_id, provider, api_key, base_url, model_name, "
                    " updated_at, updated_by_user_id) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s) "
                    "ON CONFLICT (workspace_id) DO UPDATE SET "
                    " provider=EXCLUDED.provider, api_key=EXCLUDED.api_key, "
                    " base_url=EXCLUDED.base_url, "
                    " model_name=EXCLUDED.model_name, "
                    " updated_at=EXCLUDED.updated_at, "
                    " updated_by_user_id=EXCLUDED.updated_by_user_id",
                    (rec.workspace_id, rec.provider, rec.api_key,
                     rec.base_url, rec.model_name,
                     rec.updated_at.isoformat(), rec.updated_by_user_id))
            conn.commit()
        return rec
```

- [ ] **Step 2: 验证 import 无误**

Run: `D:/software/conda_data/envs/oasis/python.exe -c "import wanxiang.api.model_config_store_pg; print('ok')"`
Expected: 打印 `ok`(import 成功,不实际连库)

- [ ] **Step 3: 提交**

```bash
git add wanxiang/api/model_config_store_pg.py
git commit -m "feat(model-config): PG store (与 SQLite 同接口)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 5: 扩展 ModelConfig schema(支持新 provider + base_url)

**Files:**
- Modify: `wanxiang/api/schemas.py:39-48`
- Test: `test/wanxiang/test_model_config_schema.py`

**Interfaces:**
- Produces: `ModelConfig` 新增字段 `base_url: str | None = None`;`provider` 取值扩展为 `Literal["stub","deepseek","openai","qwen","custom"]`;校验规则:`needs_key` 类 provider 缺 key → ValueError;`custom` 缺 base_url → ValueError。
- Consumes: `wanxiang.api.model_presets.get_preset`(Task 1)

- [ ] **Step 1: 写失败测试**

```python
# test/wanxiang/test_model_config_schema.py
import pytest
from pydantic import ValidationError
from wanxiang.api.schemas import ModelConfig


def test_stub_ok_without_key():
    assert ModelConfig(provider="stub").api_key is None


def test_deepseek_requires_key():
    with pytest.raises(ValidationError):
        ModelConfig(provider="deepseek")


def test_openai_requires_key():
    with pytest.raises(ValidationError):
        ModelConfig(provider="openai")


def test_custom_requires_base_url():
    with pytest.raises(ValidationError):
        ModelConfig(provider="custom", api_key="sk-x")


def test_custom_ok_with_key_and_base_url():
    c = ModelConfig(provider="custom", api_key="sk-x",
                    base_url="https://gw/v1")
    assert c.base_url == "https://gw/v1"


def test_qwen_ok_with_key():
    assert ModelConfig(provider="qwen", api_key="sk-x").provider == "qwen"
```

- [ ] **Step 2: 运行确认失败**

Run: `D:/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_model_config_schema.py -v`
Expected: FAIL(`test_openai_requires_key` / `test_custom_*` 失败——当前 schema 仅 stub/deepseek)

- [ ] **Step 3: 写实现** —— 替换 `wanxiang/api/schemas.py:39-48` 的 `ModelConfig` 类

```python
class ModelConfig(BaseModel):
    provider: Literal["stub", "deepseek", "openai", "qwen", "custom"]
    api_key: str | None = None
    model_name: str | None = None
    base_url: str | None = None

    @model_validator(mode="after")
    def _validate_against_preset(self):
        from wanxiang.api.model_presets import get_preset
        preset = get_preset(self.provider)
        if preset is None:
            raise ValueError(f"unknown provider: {self.provider}")
        if preset["needs_key"] and not self.api_key:
            raise ValueError(f"provider={self.provider!r} requires api_key")
        if preset["allow_custom_base_url"] and not self.base_url:
            raise ValueError(
                f"provider={self.provider!r} requires base_url")
        return self
```

- [ ] **Step 4: 运行确认通过(含回归)**

Run: `D:/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_model_config_schema.py test/wanxiang/test_tenant_model_default.py -v`
Expected: PASS(新测试 6 passed,且原 `test_tenant_model_default.py` 不回归)

- [ ] **Step 5: 提交**

```bash
git add wanxiang/api/schemas.py test/wanxiang/test_model_config_schema.py
git commit -m "feat(model-config): ModelConfig 支持 openai/qwen/custom + base_url

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 6: OpenAI 兼容 ModelCall 适配器 + deps 工厂分支

**Files:**
- Modify: `wanxiang/models/adapter.py`(新增 `make_openai_compatible_call`)
- Modify: `wanxiang/models/__init__.py`(导出)
- Modify: `wanxiang/api/deps.py:10-19`(`default_model_factory` 增加分支)
- Test: `test/wanxiang/test_model_factory_dispatch.py`

**Interfaces:**
- Consumes: `ModelConfig`(Task 5)、camel `ModelFactory` / `ModelPlatformType.OPENAI_COMPATIBLE_MODEL`
- Produces:
  - `make_openai_compatible_call(api_key, base_url, model_name, **kwargs) -> ModelCall`
  - `default_model_factory(cfg)` 对 `provider in {deepseek,openai,qwen,custom}` 走 OpenAI 兼容实现,补全预设 base_url/default_model;`stub` 走 `make_stub_call`。

- [ ] **Step 1: 写失败测试**(用 monkeypatch 拦截 camel,不发真实请求)

```python
# test/wanxiang/test_model_factory_dispatch.py
import wanxiang.models.adapter as adapter
from wanxiang.api.deps import default_model_factory
from wanxiang.api.schemas import ModelConfig


def test_stub_provider_returns_callable():
    call = default_model_factory(ModelConfig(provider="stub"))
    assert callable(call)


def test_openai_compatible_used_for_deepseek(monkeypatch):
    captured = {}

    def fake(api_key, base_url, model_name, **kw):
        captured.update(api_key=api_key, base_url=base_url,
                        model_name=model_name)
        return lambda messages: "x"

    monkeypatch.setattr(adapter, "make_openai_compatible_call", fake)
    monkeypatch.setattr("wanxiang.api.deps.make_openai_compatible_call", fake)
    default_model_factory(ModelConfig(provider="deepseek", api_key="sk-1"))
    assert captured["base_url"] == "https://api.deepseek.com/v1"
    assert captured["model_name"] == "deepseek-chat"
    assert captured["api_key"] == "sk-1"


def test_custom_passes_through_base_url(monkeypatch):
    captured = {}

    def fake(api_key, base_url, model_name, **kw):
        captured.update(base_url=base_url, model_name=model_name)
        return lambda messages: "x"

    monkeypatch.setattr("wanxiang.api.deps.make_openai_compatible_call", fake)
    default_model_factory(ModelConfig(
        provider="custom", api_key="sk-1",
        base_url="https://gw/v1", model_name="my-model"))
    assert captured["base_url"] == "https://gw/v1"
    assert captured["model_name"] == "my-model"
```

- [ ] **Step 2: 运行确认失败**

Run: `D:/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_model_factory_dispatch.py -v`
Expected: FAIL(`make_openai_compatible_call` 不存在 / deps 未分支)

- [ ] **Step 3a: adapter 新增工厂** —— 在 `wanxiang/models/adapter.py` 末尾追加

```python
def make_openai_compatible_call(
    api_key: str,
    base_url: str,
    model_name: str,
    **kwargs: Any,
) -> ModelCall:
    """OpenAI 兼容网关(DeepSeek/OpenAI/通义/自建 vLLM 等)统一工厂。

    用 camel 的 OPENAI_COMPATIBLE_MODEL 平台,凭 base_url + api_key 接入。
    不在构造时发请求——只在 await 返回的 call 时。
    """
    backend = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
        model_type=model_name,
        api_key=api_key,
        url=base_url,
        **kwargs,
    )
    return wrap_camel_model(backend)
```

- [ ] **Step 3b: 导出** —— 改 `wanxiang/models/__init__.py`

```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""models: camel BaseModelBackend → ModelCall 适配器（spec §M7 模型可配置）。"""
from wanxiang.models.adapter import (make_deepseek_call,
                                      make_openai_compatible_call,
                                      make_stub_call, wrap_camel_model)

__all__ = ["wrap_camel_model", "make_stub_call", "make_deepseek_call",
           "make_openai_compatible_call"]
```

- [ ] **Step 3c: deps 分支** —— 替换 `wanxiang/api/deps.py` 的 `default_model_factory`(顶部 import 同步加 `make_openai_compatible_call`)

```python
from wanxiang.models import (make_deepseek_call, make_openai_compatible_call,
                             make_stub_call)
# ... (其余 import 不变)


def default_model_factory(cfg: ModelConfig) -> ModelCall:
    """根据 ModelConfig 选择 ModelCall 实现。测试可 monkeypatch 此函数。"""
    if cfg.provider == "stub":
        return make_stub_call()
    from wanxiang.api.model_presets import get_preset
    preset = get_preset(cfg.provider) or {}
    base_url = cfg.base_url or preset.get("base_url")
    model_name = cfg.model_name or preset.get("default_model")
    if not base_url or not model_name:
        raise ValueError(
            f"provider={cfg.provider!r} 缺 base_url/model_name")
    return make_openai_compatible_call(
        api_key=cfg.api_key, base_url=base_url, model_name=model_name)
```

- [ ] **Step 4: 运行确认通过**

Run: `D:/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_model_factory_dispatch.py -v`
Expected: PASS(3 passed)

- [ ] **Step 5: 提交**

```bash
git add wanxiang/models/adapter.py wanxiang/models/__init__.py wanxiang/api/deps.py test/wanxiang/test_model_factory_dispatch.py
git commit -m "feat(model-config): OpenAI 兼容适配器 + deps 工厂按 provider 分发

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 7: app.py 接线 model_config_store

**Files:**
- Modify: `wanxiang/api/app.py:67-68 附近`(加 store 初始化)、`app.py:240-250 附近`(挂路由,路由在 Task 8 创建)
- Test: `test/wanxiang/test_app_model_config_wiring.py`

**Interfaces:**
- Consumes: `make_model_config_store`(Task 2)
- Produces: `app.state.model_config_store` 可用。

> 注:本任务只接 store + 预留路由挂载块(`try/except`,Task 8 前路由不存在不影响启动)。

- [ ] **Step 1: 写失败测试**

```python
# test/wanxiang/test_app_model_config_wiring.py
from wanxiang.api.app import create_app


def test_app_has_model_config_store():
    app = create_app()
    assert hasattr(app.state, "model_config_store")
    assert app.state.model_config_store.get("nope") is None
```

- [ ] **Step 2: 运行确认失败**

Run: `D:/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_app_model_config_wiring.py -v`
Expected: FAIL — `AttributeError: model_config_store`

- [ ] **Step 3a: 加 store 初始化** —— 在 `app.py` 的 `app.state.api_key_store = make_api_key_store(...)` 之后(约 68 行后)插入

```python
    # 模型配置 store(每工作区一份大模型 provider+key);与其他 store 共享 DSN
    from wanxiang.api.model_config import make_model_config_store
    app.state.model_config_store = make_model_config_store(
        os.environ.get("WANXIANG_TASKS_DB"))
```

- [ ] **Step 3b: 预留路由挂载** —— 在 `api_keys` 路由挂载块(约 246-250 行)之后插入

```python
    # 模型配置路由(/v1/workspaces/{slug}/model-config + /v1/model-presets)
    try:
        from wanxiang.api.routes.model_config import (
            router as model_config_router)
        app.include_router(model_config_router, prefix="/v1")
    except Exception:
        pass
```

- [ ] **Step 4: 运行确认通过**

Run: `D:/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_app_model_config_wiring.py -v`
Expected: PASS(1 passed)

- [ ] **Step 5: 提交**

```bash
git add wanxiang/api/app.py test/wanxiang/test_app_model_config_wiring.py
git commit -m "feat(model-config): app.py 接线 store + 预留路由挂载

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 8: 路由 model_config.py(GET presets / GET-PUT config)

**Files:**
- Create: `wanxiang/api/routes/model_config.py`
- Test: `test/wanxiang/test_model_config_routes.py`

**Interfaces:**
- Consumes: `MODEL_PRESETS` / `get_preset` / `mask_key`(Task 1)、`ModelConfigRecord`(Task 2)、`require_user`(`auth_user.py`)、`resolve_workspace` 校验逻辑(复用 workspaces helper 思路:`get_by_slug` + `get_member` + role)、`app.state.model_config_store`、`app.state.workspace_store`。
- Produces 路由:
  - `GET /v1/model-presets` → `{presets: MODEL_PRESETS}`(登录可读)
  - `GET /v1/workspaces/{slug}/model-config` → `{provider, api_key_masked, base_url, model_name, has_key, updated_at, updated_by}`(member 可读,key 脱敏);未配置时返回默认 `{provider:"stub", has_key:false, ...}`
  - `PUT /v1/workspaces/{slug}/model-config`(owner/admin)入参 `{provider, api_key?, base_url?, model_name?}`;key 留空=不改旧 key;返回脱敏后的当前配置。

- [ ] **Step 1: 写失败测试**(用 FastAPI TestClient + 注册两用户造 owner/member)

```python
# test/wanxiang/test_model_config_routes.py
from fastapi.testclient import TestClient
from wanxiang.api.app import create_app


def _client():
    return TestClient(create_app())


def _register(c, email):
    r = c.post("/v1/auth/register", json={
        "email": email, "password": "Test1234!",
        "display_name": email.split("@")[0], "locale": "zh"})
    assert r.status_code == 200, r.text
    d = r.json()
    slug = (d.get("default_workspace") or d["workspaces"][0])["slug"]
    return d["access_token"], slug


def _auth(tok):
    return {"Authorization": f"Bearer {tok}"}


def test_presets_requires_login():
    c = _client()
    assert c.get("/v1/model-presets").status_code == 401


def test_presets_listed_when_logged_in():
    c = _client()
    tok, _ = _register(c, "p1@example.com")
    r = c.get("/v1/model-presets", headers=_auth(tok))
    assert r.status_code == 200
    ids = {p["id"] for p in r.json()["presets"]}
    assert "deepseek" in ids and "custom" in ids


def test_get_config_default_when_unset():
    c = _client()
    tok, slug = _register(c, "p2@example.com")
    r = c.get(f"/v1/workspaces/{slug}/model-config", headers=_auth(tok))
    assert r.status_code == 200
    body = r.json()
    assert body["provider"] == "stub"
    assert body["has_key"] is False


def test_put_then_get_masks_key():
    c = _client()
    tok, slug = _register(c, "p3@example.com")
    r = c.put(f"/v1/workspaces/{slug}/model-config", headers=_auth(tok),
              json={"provider": "deepseek", "api_key": "sk-abcdef1234"})
    assert r.status_code == 200, r.text
    g = c.get(f"/v1/workspaces/{slug}/model-config",
              headers=_auth(tok)).json()
    assert g["provider"] == "deepseek"
    assert g["has_key"] is True
    assert g["api_key_masked"] == "sk-…1234"
    assert "api_key" not in g  # 完整 key 绝不出现


def test_put_blank_key_keeps_existing():
    c = _client()
    tok, slug = _register(c, "p4@example.com")
    c.put(f"/v1/workspaces/{slug}/model-config", headers=_auth(tok),
          json={"provider": "deepseek", "api_key": "sk-keep0001"})
    # 第二次只改 model_name,不传 key
    r = c.put(f"/v1/workspaces/{slug}/model-config", headers=_auth(tok),
              json={"provider": "deepseek", "model_name": "deepseek-chat"})
    assert r.status_code == 200, r.text
    g = c.get(f"/v1/workspaces/{slug}/model-config",
              headers=_auth(tok)).json()
    assert g["api_key_masked"] == "sk-…0001"  # 旧 key 仍在
    assert g["model_name"] == "deepseek-chat"


def test_put_invalid_provider_400():
    c = _client()
    tok, slug = _register(c, "p5@example.com")
    r = c.put(f"/v1/workspaces/{slug}/model-config", headers=_auth(tok),
              json={"provider": "nope", "api_key": "x"})
    assert r.status_code == 400


def test_put_deepseek_without_key_400_when_none_stored():
    c = _client()
    tok, slug = _register(c, "p6@example.com")
    r = c.put(f"/v1/workspaces/{slug}/model-config", headers=_auth(tok),
              json={"provider": "deepseek"})
    assert r.status_code == 400


def test_put_custom_without_base_url_400():
    c = _client()
    tok, slug = _register(c, "p7@example.com")
    r = c.put(f"/v1/workspaces/{slug}/model-config", headers=_auth(tok),
              json={"provider": "custom", "api_key": "sk-x"})
    assert r.status_code == 400
```

- [ ] **Step 2: 运行确认失败**

Run: `D:/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_model_config_routes.py -v`
Expected: FAIL — 路由不存在(404)

- [ ] **Step 3: 写实现**

```python
# wanxiang/api/routes/model_config.py
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""模型配置路由:provider 预设 + 每工作区 provider/key 读写。

- GET /v1/model-presets                      登录可读
- GET /v1/workspaces/{slug}/model-config     member 可读(key 脱敏)
- PUT /v1/workspaces/{slug}/model-config     owner/admin 可写
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from wanxiang.api.auth_user import require_user
from wanxiang.api.i18n import get_request_locale, t
from wanxiang.api.model_config import ModelConfigRecord
from wanxiang.api.model_presets import MODEL_PRESETS, get_preset, mask_key

router = APIRouter()


class ModelConfigPut(BaseModel):
    provider: str
    api_key: str | None = None
    base_url: str | None = None
    model_name: str | None = None


def _resolve_member(slug: str, request: Request, user, locale):
    ws = request.app.state.workspace_store.get_by_slug(slug)
    if not ws:
        raise HTTPException(status_code=404, detail="workspace not found")
    m = request.app.state.workspace_store.get_member(
        ws.workspace_id, user.user_id)
    if not m:
        raise HTTPException(
            status_code=403, detail=t("workspace.not_a_member", locale=locale))
    return ws, m


def _serialize(rec: ModelConfigRecord | None) -> dict:
    if rec is None:
        return {"provider": "stub", "api_key_masked": None,
                "base_url": None, "model_name": None, "has_key": False,
                "updated_at": None, "updated_by": None}
    return {
        "provider": rec.provider,
        "api_key_masked": mask_key(rec.api_key),
        "base_url": rec.base_url,
        "model_name": rec.model_name,
        "has_key": bool(rec.api_key),
        "updated_at": rec.updated_at.isoformat() if rec.updated_at else None,
        "updated_by": rec.updated_by_user_id,
    }


@router.get("/model-presets")
def list_presets(request: Request, user=Depends(require_user)):
    return {"presets": MODEL_PRESETS}


@router.get("/workspaces/{slug}/model-config")
def get_model_config(slug: str, request: Request,
                     user=Depends(require_user)):
    locale = get_request_locale(request)
    ws, _ = _resolve_member(slug, request, user, locale)
    rec = request.app.state.model_config_store.get(ws.workspace_id)
    return _serialize(rec)


@router.put("/workspaces/{slug}/model-config")
def put_model_config(slug: str, body: ModelConfigPut, request: Request,
                     user=Depends(require_user)):
    locale = get_request_locale(request)
    ws, member = _resolve_member(slug, request, user, locale)
    if member.role not in ("owner", "admin"):
        raise HTTPException(
            status_code=403, detail=t("workspace.requires_admin",
                                      locale=locale))

    preset = get_preset(body.provider)
    if preset is None:
        raise HTTPException(status_code=400,
                            detail=f"unknown provider: {body.provider}")

    store = request.app.state.model_config_store
    existing = store.get(ws.workspace_id)
    # key 留空 = 不改旧 key
    api_key = body.api_key if body.api_key else (
        existing.api_key if existing else None)

    if preset["needs_key"] and not api_key:
        raise HTTPException(
            status_code=400,
            detail=t("model_config.key_required", locale=locale))
    base_url = body.base_url or (preset["base_url"])
    if preset["allow_custom_base_url"] and not body.base_url:
        raise HTTPException(
            status_code=400,
            detail=t("model_config.base_url_required", locale=locale))

    rec = ModelConfigRecord(
        workspace_id=ws.workspace_id,
        provider=body.provider,
        api_key=api_key,
        base_url=base_url,
        model_name=body.model_name,
        updated_at=datetime.now(timezone.utc),
        updated_by_user_id=user.user_id,
    )
    store.upsert(rec)
    return _serialize(rec)
```

并在 i18n 增加文案键(若 `t()` 缺键会回退键名,不致命,但补上更好)——见 Task 11。

- [ ] **Step 4: 运行确认通过**

Run: `D:/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_model_config_routes.py -v`
Expected: PASS(9 passed)

- [ ] **Step 5: 提交**

```bash
git add wanxiang/api/routes/model_config.py test/wanxiang/test_model_config_routes.py
git commit -m "feat(model-config): 路由 GET presets + GET/PUT workspace model-config

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 9: 打通工作区默认级(simulate / simulations / sweep / chat 用 workspace 配置)

**Files:**
- Modify: `wanxiang/api/routes/simulate.py`(simulate handler 解析点)
- Modify: `wanxiang/api/routes/simulations.py`(async + sweep 解析点)
- Modify: `wanxiang/api/routes/sandboxes.py:194-201`(chat_simulate intent + sim 解析点)
- Create: `wanxiang/api/model_resolve.py`(共享辅助)
- Test: `test/wanxiang/test_workspace_model_resolve.py`

**Interfaces:**
- Consumes: `app.state.model_config_store`、`ModelConfig`(Task 5)、`ModelConfigRecord`(Task 2)
- Produces: `resolve_workspace_model(req_model, workspace_id, store) -> ModelConfig` —— 优先级:请求 model > 工作区配置(从 store 读组装)> stub。

> 背景:现有 `resolve_effective_model(req_model, tenant)` 读 `tenant.default_model_config`,但 `auth.py:88` 写死 `None`。本任务新增按 workspace_id 直读 store 的辅助,在各 handler 用它,绕过断掉的 tenant 链。

- [ ] **Step 1: 写失败测试**

```python
# test/wanxiang/test_workspace_model_resolve.py
from datetime import datetime, timezone
from wanxiang.api.model_config import (ModelConfigRecord,
                                        make_model_config_store)
from wanxiang.api.model_resolve import resolve_workspace_model
from wanxiang.api.schemas import ModelConfig


def _store_with(ws, **kw):
    s = make_model_config_store(None)
    s.upsert(ModelConfigRecord(
        workspace_id=ws, provider=kw.get("provider", "deepseek"),
        api_key=kw.get("api_key", "sk-x"),
        base_url=kw.get("base_url"), model_name=kw.get("model_name"),
        updated_at=datetime.now(timezone.utc), updated_by_user_id="u"))
    return s


def test_request_model_wins():
    s = _store_with("ws1", provider="deepseek", api_key="sk-store")
    req = ModelConfig(provider="stub")
    out = resolve_workspace_model(req, "ws1", s)
    assert out.provider == "stub"


def test_falls_back_to_workspace_config():
    s = _store_with("ws1", provider="deepseek", api_key="sk-store")
    out = resolve_workspace_model(None, "ws1", s)
    assert out.provider == "deepseek"
    assert out.api_key == "sk-store"


def test_falls_back_to_stub_when_unset():
    s = make_model_config_store(None)
    out = resolve_workspace_model(None, "ws-none", s)
    assert out.provider == "stub"
```

- [ ] **Step 2: 运行确认失败**

Run: `D:/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_workspace_model_resolve.py -v`
Expected: FAIL — `ModuleNotFoundError: wanxiang.api.model_resolve`

- [ ] **Step 3a: 写共享辅助**

```python
# wanxiang/api/model_resolve.py
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""工作区级模型解析:请求 model > 工作区配置 > stub。

替代断掉的 tenant.default_model_config 链(auth.py 写死 None),
直接按 workspace_id 从 model_config_store 读取。
"""
from __future__ import annotations


def resolve_workspace_model(req_model, workspace_id, store):
    """返回一个非空 ModelConfig。

    - req_model 非空 → 直接用(请求 wins)。
    - 否则 store 有该 workspace 配置 → 组装 ModelConfig。
    - 否则 → ModelConfig(provider="stub")。
    """
    from wanxiang.api.schemas import ModelConfig
    if req_model is not None:
        return req_model
    rec = store.get(workspace_id) if (store and workspace_id) else None
    if rec is not None:
        return ModelConfig(
            provider=rec.provider,
            api_key=rec.api_key,
            base_url=rec.base_url,
            model_name=rec.model_name,
        )
    return ModelConfig(provider="stub")
```

- [ ] **Step 3b: 接入 chat_simulate** —— 改 `wanxiang/api/routes/sandboxes.py:194-201`,把写死的 stub 换成工作区解析

```python
    # Parse intent —— 用工作区默认模型(请求未带 model 时)
    from wanxiang.api.schemas import ModelConfig
    from wanxiang.api.model_resolve import resolve_workspace_model
    from wanxiang.chat.intent import parse_intent
    req_model = None
    if req.model:
        try:
            req_model = ModelConfig(**req.model)
        except Exception:
            req_model = None
    model_cfg = resolve_workspace_model(
        req_model, ws.workspace_id, request.app.state.model_config_store)
    model_call = model_factory(model_cfg)
```

并把后续 `run_simulation_pipeline(sim_req, ...)` 之前确保 `sim_req.model` 也用同一 `model_cfg`:在 `sim_req = intent.request` 之后插入 `sim_req.model = model_cfg`(覆盖,使真实模拟也走工作区配置)。

- [ ] **Step 3c: 接入 simulate / simulations / sweep** —— 这些 handler 当前用 `resolve_effective_model(req.model, tenant)`。在每处改为先尝试工作区解析:

`wanxiang/api/routes/simulate.py`(simulate handler,约 255-257 行):
```python
        from wanxiang.api.model_resolve import resolve_workspace_model
        req = req.model_copy(update={
            "model": resolve_workspace_model(
                req.model, tenant.tenant_id,
                request.app.state.model_config_store)})
```
(`tenant.tenant_id` 在新 workspace 路径下即 workspace_id,见 `auth.py:83`。)

`wanxiang/api/routes/simulations.py` 的 async handler(约 227-237)与 sweep handler(约 294)同样把 `resolve_effective_model(req.model, tenant)` 换成 `resolve_workspace_model(req.model, tenant.tenant_id, request.app.state.model_config_store)`。

- [ ] **Step 4: 运行确认通过(含回归)**

Run: `D:/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_workspace_model_resolve.py test/wanxiang/test_tenant_model_default.py -v`
Expected: PASS(新 3 passed;原 tenant 测试不回归)

- [ ] **Step 5: 提交**

```bash
git add wanxiang/api/model_resolve.py wanxiang/api/routes/simulate.py wanxiang/api/routes/simulations.py wanxiang/api/routes/sandboxes.py test/wanxiang/test_workspace_model_resolve.py
git commit -m "feat(model-config): 打通工作区默认级(simulate/sweep/chat 用 workspace 配置)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 10: 前端 — 去掉写死 stub + API client 方法

**Files:**
- Modify: `frontend/src/pages/LandingPage.tsx:172`
- Modify: `frontend/src/pages/sandbox/SandboxPage.tsx`(确认不传 model;若已不传则免改)
- Test: 手动 + Task 11 的渲染测试覆盖

**Interfaces:**
- Produces: 聊天发送不再写死 `provider:'stub'`;后端回落工作区默认。

- [ ] **Step 1: 改 LandingPage** —— `frontend/src/pages/LandingPage.tsx:172`

把:
```tsx
        { text, model: { provider: 'stub' } }
```
改为:
```tsx
        { text }
```

- [ ] **Step 2: 核对 SandboxPage**

Run: `grep -n "model" frontend/src/pages/sandbox/SandboxPage.tsx`
Expected: 聊天 post 不含 `model` 字段(若含写死 stub 则同样删除该字段)。

- [ ] **Step 3: 前端类型检查**

Run: `cd frontend && npm run lint`
Expected: 无新增 TS 报错。

- [ ] **Step 4: 提交**

```bash
git add frontend/src/pages/LandingPage.tsx frontend/src/pages/sandbox/SandboxPage.tsx
git commit -m "feat(model-config): 前端去掉写死 stub,聊天用工作区默认模型

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 11: 前端 — SettingsView 模型配置卡片 + i18n

**Files:**
- Modify: `frontend/src/views/SettingsView.tsx`(加"模型配置"卡片)
- Modify: `frontend/src/locales/zh.json` / `frontend/src/locales/en.json`(新增文案)
- Modify: `wanxiang/api/i18n.py`(后端 `model_config.key_required` / `base_url_required` 文案)
- Test: `frontend/src/views/SettingsView.test.tsx`

**Interfaces:**
- Consumes: `GET /v1/model-presets`、`GET/PUT /v1/workspaces/{slug}/model-config`(Task 8)、当前用户 role(`GET /v1/workspaces/{slug}/members` 或复用 `ownerId` 已有逻辑判断 owner;admin 需读 members)。
- Produces: 设置页可见且可用的模型配置卡片。

- [ ] **Step 1: 写渲染测试(vitest)**

```tsx
// frontend/src/views/SettingsView.test.tsx
// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('@/lib/api', () => ({
  api: {
    get: vi.fn((url: string) => {
      if (url.includes('/model-presets')) {
        return Promise.resolve({ data: { presets: [
          { id: 'stub', label: '测试桩', base_url: null,
            default_model: null, needs_key: false,
            allow_custom_base_url: false },
          { id: 'deepseek', label: 'DeepSeek',
            base_url: 'https://api.deepseek.com/v1',
            default_model: 'deepseek-chat', needs_key: true,
            allow_custom_base_url: false },
        ] } })
      }
      if (url.includes('/model-config')) {
        return Promise.resolve({ data: {
          provider: 'stub', api_key_masked: null, base_url: null,
          model_name: null, has_key: false, updated_at: null,
          updated_by: null } })
      }
      if (/\/workspaces\/[^/]+$/.test(url)) {
        return Promise.resolve({ data: { owner_user_id: 'u1' } })
      }
      return Promise.resolve({ data: {} })
    }),
    patch: vi.fn(() => Promise.resolve({ data: {} })),
    put: vi.fn(() => Promise.resolve({ data: {} })),
    delete: vi.fn(() => Promise.resolve({ data: {} })),
  },
}))

vi.mock('@/stores/authStore', () => ({
  useAuthStore: (sel: any) => sel({
    user: { user_id: 'u1' },
    workspaces: [{ slug: 'reptest', name: 'RT', locale: 'zh',
                   type: 'personal' }],
    setWorkspaces: vi.fn(),
  }),
}))

import { SettingsView } from './SettingsView'

describe('SettingsView model config card', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renders provider select after load', async () => {
    render(<SettingsView slug="reptest" />)
    await waitFor(() =>
      expect(screen.getByTestId('model-provider-select')).toBeTruthy())
  })
})
```

- [ ] **Step 2: 运行确认失败**

Run: `cd frontend && npx vitest run src/views/SettingsView.test.tsx`
Expected: FAIL — 找不到 `model-provider-select`

- [ ] **Step 3a: i18n 文案** —— 在 `frontend/src/locales/zh.json` 增加(en.json 加对应英文)

```json
  "settings.model_title": "模型配置",
  "settings.model_subtitle": "为本工作区配置大模型 provider 与 API Key,聊天与模拟将使用它",
  "settings.model_provider": "Provider",
  "settings.model_api_key": "API Key",
  "settings.model_api_key_hint": "已配置时留空表示不修改",
  "settings.model_base_url": "Base URL",
  "settings.model_model_name": "模型名称(可选)",
  "settings.model_saved": "模型配置已保存",
  "settings.model_readonly_hint": "仅工作区管理员可修改模型配置",
```

后端 `wanxiang/api/i18n.py` 增加 `model_config.key_required`(zh:"该 provider 需要 API Key" / en:"This provider requires an API key")与 `model_config.base_url_required`(zh:"自定义网关需填写 Base URL" / en:"Custom gateway requires a base URL"),按该文件现有结构(键 → {zh,en})添加。

- [ ] **Step 3b: SettingsView 卡片** —— 在 `SettingsView.tsx` 现有第一张 `GlassCard`(name/locale 表单)之后插入新卡片。新增 state 与 effect(顶部),并新增 JSX。关键片段:

```tsx
  // ── model config state ──
  const [presets, setPresets] = useState<Array<{
    id: string; label: string; base_url: string | null;
    default_model: string | null; needs_key: boolean;
    allow_custom_base_url: boolean }>>([])
  const [mcProvider, setMcProvider] = useState('stub')
  const [mcKey, setMcKey] = useState('')
  const [mcKeyMasked, setMcKeyMasked] = useState<string | null>(null)
  const [mcBaseUrl, setMcBaseUrl] = useState('')
  const [mcModelName, setMcModelName] = useState('')
  const [mcSaving, setMcSaving] = useState(false)
  const [myRole, setMyRole] = useState<string>('member')

  useEffect(() => {
    api.get('/model-presets')
      .then((r) => setPresets(r.data.presets ?? []))
      .catch(() => { /* non-fatal */ })
  }, [])

  useEffect(() => {
    if (!slug) return
    api.get(`/workspaces/${slug}/model-config`).then((r) => {
      setMcProvider(r.data.provider ?? 'stub')
      setMcKeyMasked(r.data.api_key_masked ?? null)
      setMcBaseUrl(r.data.base_url ?? '')
      setMcModelName(r.data.model_name ?? '')
    }).catch(() => { /* non-fatal */ })
    api.get(`/workspaces/${slug}/members`).then((r) => {
      const me = (r.data.members ?? []).find(
        (m: { user_id: string }) => m.user_id === user?.user_id)
      if (me) setMyRole(me.role)
    }).catch(() => { /* non-fatal */ })
  }, [slug, user?.user_id])

  const canEditModel = myRole === 'owner' || myRole === 'admin'
  const curPreset = presets.find((p) => p.id === mcProvider)

  async function handleSaveModel(e: FormEvent) {
    e.preventDefault()
    if (!slug) return
    setMcSaving(true)
    try {
      const payload: Record<string, unknown> = { provider: mcProvider }
      if (mcKey) payload.api_key = mcKey
      if (curPreset?.allow_custom_base_url) payload.base_url = mcBaseUrl
      if (mcModelName) payload.model_name = mcModelName
      const r = await api.put(
        `/workspaces/${slug}/model-config`, payload)
      setMcKey('')
      setMcKeyMasked(r.data.api_key_masked ?? null)
      toast.success(t('settings.model_saved'))
    } catch (err) {
      const ex = err as { response?: { data?: { detail?: string } } }
      toast.error(ex.response?.data?.detail ?? t('common.error'))
    } finally {
      setMcSaving(false)
    }
  }
```

JSX(插在 name/locale 卡片后):
```tsx
      <GlassCard className="mt-6">
        <div className="wx-page-header" style={{ marginBottom: 12 }}>
          <div>
            <h2 className="wx-page-title" style={{ fontSize: 18 }}>
              {t('settings.model_title')}
            </h2>
            <p className="wx-page-subtitle">{t('settings.model_subtitle')}</p>
          </div>
        </div>
        {!canEditModel && (
          <p className="text-sm" style={{ color: 'var(--wx-text-secondary)',
               marginBottom: 12 }}>
            {t('settings.model_readonly_hint')}
          </p>
        )}
        <form onSubmit={handleSaveModel}>
          <FormField label={t('settings.model_provider')}>
            <select
              data-testid="model-provider-select"
              className="wx-input"
              value={mcProvider}
              disabled={!canEditModel}
              onChange={(e) => setMcProvider(e.target.value)}
            >
              {presets.map((p) => (
                <option key={p.id} value={p.id}>{p.label}</option>
              ))}
            </select>
          </FormField>
          {curPreset?.needs_key && (
            <FormField label={t('settings.model_api_key')}
                       hint={t('settings.model_api_key_hint')}>
              <input
                className="wx-input"
                type="password"
                value={mcKey}
                disabled={!canEditModel}
                placeholder={mcKeyMasked ?? ''}
                onChange={(e) => setMcKey(e.target.value)}
              />
            </FormField>
          )}
          {curPreset?.allow_custom_base_url && (
            <FormField label={t('settings.model_base_url')}>
              <input
                className="wx-input"
                value={mcBaseUrl}
                disabled={!canEditModel}
                placeholder="https://your-gateway/v1"
                onChange={(e) => setMcBaseUrl(e.target.value)}
              />
            </FormField>
          )}
          <FormField label={t('settings.model_model_name')}>
            <input
              className="wx-input"
              value={mcModelName}
              disabled={!canEditModel}
              placeholder={curPreset?.default_model ?? ''}
              onChange={(e) => setMcModelName(e.target.value)}
            />
          </FormField>
          {canEditModel && (
            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button type="submit" className="wx-btn-primary"
                      disabled={mcSaving}>
                {mcSaving ? t('common.loading') : t('common.submit')}
              </button>
            </div>
          )}
        </form>
      </GlassCard>
```

- [ ] **Step 4: 运行确认通过**

Run: `cd frontend && npx vitest run src/views/SettingsView.test.tsx`
Expected: PASS(1 passed)

- [ ] **Step 5: 类型检查 + 提交**

```bash
cd frontend && npm run lint
cd .. && git add frontend/src/views/SettingsView.tsx frontend/src/views/SettingsView.test.tsx frontend/src/locales/zh.json frontend/src/locales/en.json wanxiang/api/i18n.py
git commit -m "feat(model-config): 设置页模型配置卡片 + i18n 文案

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 12: 端到端验证 + Docker 重建

**Files:** 无新增(集成验证)

- [ ] **Step 1: 跑全量后端单测**

Run: `D:/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/ -q`
Expected: 全绿(含本特性新测试,无回归)

- [ ] **Step 2: 跑前端单测**

Run: `cd frontend && npx vitest run`
Expected: 全绿

- [ ] **Step 3: Docker 重建并起栈**

Run: `docker compose up -d --build`
Expected: 4 容器 healthy(`docker compose ps`)

- [ ] **Step 4: 冒烟脚本**(注册 → PUT 配置 → GET 脱敏 → presets)

```bash
B="http://localhost:8000/v1"; CURL="curl -s --noproxy *"
TOK=$(curl -s --noproxy '*' -X POST "$B/auth/register" -H 'Content-Type: application/json' \
  -d '{"email":"mc-smoke@example.com","password":"Test1234!","display_name":"MC","locale":"zh"}' \
  | "D:/software/conda_data/envs/oasis/python.exe" -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
SLUG=mc
curl -s --noproxy '*' "$B/model-presets" -H "Authorization: Bearer $TOK" | head -c 200; echo
curl -s --noproxy '*' -X PUT "$B/workspaces/$SLUG/model-config" -H "Authorization: Bearer $TOK" \
  -H 'Content-Type: application/json' -d '{"provider":"deepseek","api_key":"sk-smoke1234"}' ; echo
curl -s --noproxy '*' "$B/workspaces/$SLUG/model-config" -H "Authorization: Bearer $TOK"; echo
```
Expected:presets 含 deepseek;PUT 返回 `api_key_masked:"sk-…1234"` 且**无** `api_key` 完整值;GET 同样脱敏、`has_key:true`。

- [ ] **Step 5: 浏览器人工确认**

打开 `http://localhost:8000/`(强刷)→ 登录 → 设置页可见"模型配置"卡片;切到 DeepSeek 出现 API Key 框、切到"自定义"出现 Base URL 框;保存成功 toast;member 账号看到只读提示。

- [ ] **Step 6: 提交(若有微调)**

```bash
git add -A
git commit -m "test(model-config): 端到端验证通过(全量单测 + Docker 冒烟)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage(逐节核对 spec → 任务):**
- §4.1 新表 → Task 3/4 ✅;§4.2 预设表 → Task 1 ✅;§4.3 store → Task 2/3/4 ✅
- §5.1 三路由 → Task 8 ✅;§5.2 OpenAI 兼容 + 解析链 → Task 6/9 ✅;§5.3 脱敏 → Task 1(mask_key)+ Task 8(_serialize 不含完整 key)✅
- §6.1 设置卡片 → Task 11 ✅;§6.2 权限适配 → Task 11(canEditModel)✅;§6.3 去 stub → Task 10 ✅;§6.4 i18n → Task 11 ✅
- §7 错误处理 → Task 8(400/403 校验)+ Task 11(前端 toast)✅;LLM 失败已由现有 sandboxes try/except 兜住
- §8 测试 → 各任务 TDD + Task 12 集成 ✅
- §9 OASIS 关系 → 设计说明,无需代码 ✅

**Placeholder scan:** 无 TBD/TODO;每个代码步骤含完整代码。注:Task 8 Step 2 有一处笔误命令已在其下方给出更正命令(正确 Python 路径)。

**Type consistency:** `ModelConfigRecord` 字段在 Task 2/3/4/8/9 一致;`make_model_config_store` 签名一致;`resolve_workspace_model(req_model, workspace_id, store)` 在 Task 9 定义并调用一致;`mask_key` 输出格式 `sk-…1234` 在 Task 1 定义、Task 8 测试断言一致;前端 `api_key_masked`/`has_key` 字段在 Task 8 后端与 Task 11 前端一致。

**Scope:** 聚焦单一特性(工作区模型 key 配置),12 个任务可独立测试。
