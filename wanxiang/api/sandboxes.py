# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""Sandbox = workspace-scoped persistent scenario container (P6).

A sandbox holds:
- Identity: name, emoji icon, description
- Default scenario config (so re-runs reuse same params)
- N total population size (e.g. 50000 virtual people)
- Distribution config (which yaml to sample from)
- A history of simulations (linked by sandbox_id)
- A chat history (NL conversation with the AI officer)

Mirrors ``workspaces.py`` factory pattern (InMemory / Sqlite / Pg).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Literal
from urllib.parse import urlparse


@dataclass
class Sandbox:
    sandbox_id: str
    workspace_id: str
    name: str
    emoji: str = "🥤"
    description: str = ""
    distribution_path: str = "cn_national_joint_2020"
    population_size: int = 1000
    created_by_user_id: str | None = None
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc))
    last_active_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc))
    archived: bool = False
    # 所属分组(预测任务分组管理);None = 未分组
    group_id: str | None = None

    def to_dict(self) -> dict:
        return {
            "sandbox_id": self.sandbox_id,
            "workspace_id": self.workspace_id,
            "name": self.name,
            "emoji": self.emoji,
            "description": self.description,
            "distribution_path": self.distribution_path,
            "population_size": self.population_size,
            "created_by_user_id": self.created_by_user_id,
            "created_at": self.created_at.isoformat(),
            "last_active_at": self.last_active_at.isoformat(),
            "archived": self.archived,
            "group_id": self.group_id,
        }


@dataclass
class SandboxGroup:
    """预测任务分组(类似 ChatGPT 项目/文件夹)。"""
    group_id: str
    workspace_id: str
    name: str
    created_by_user_id: str | None = None
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "group_id": self.group_id,
            "workspace_id": self.workspace_id,
            "name": self.name,
            "created_by_user_id": self.created_by_user_id,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ChatMessage:
    message_id: str
    sandbox_id: str
    role: Literal["user", "assistant", "system"]
    content: str
    kind: Literal["text", "intent_parsed", "simulation_started",
                  "simulation_progress", "simulation_done",
                  "report_card", "error"] = "text"
    metadata: dict = field(default_factory=dict)
    user_id: str | None = None
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "message_id": self.message_id,
            "sandbox_id": self.sandbox_id,
            "role": self.role,
            "content": self.content,
            "kind": self.kind,
            "metadata": self.metadata,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
        }


class InMemorySandboxStore:
    """Manages sandboxes + chat messages in-process (test default)."""

    def __init__(self):
        self._sb: dict[str, Sandbox] = {}
        self._msgs: list[ChatMessage] = []
        self._groups: dict[str, SandboxGroup] = {}
        self._lock = Lock()

    def create_sandbox(self, sb: Sandbox) -> Sandbox:
        if sb.sandbox_id == "auto":
            sb.sandbox_id = uuid.uuid4().hex
        with self._lock:
            self._sb[sb.sandbox_id] = sb
        return sb

    def get_sandbox(self, sandbox_id: str) -> Sandbox | None:
        return self._sb.get(sandbox_id)

    def list_for_workspace(self, workspace_id: str,
                            *, include_archived: bool = False
                            ) -> list[Sandbox]:
        with self._lock:
            items = [s for s in self._sb.values()
                     if s.workspace_id == workspace_id
                     and (include_archived or not s.archived)]
        return sorted(items, key=lambda s: s.last_active_at, reverse=True)

    def update_sandbox(self, sandbox_id: str, **fields) -> Sandbox | None:
        with self._lock:
            sb = self._sb.get(sandbox_id)
            if not sb:
                return None
            for k, v in fields.items():
                if hasattr(sb, k):
                    setattr(sb, k, v)
            return sb

    def delete_sandbox(self, sandbox_id: str) -> bool:
        with self._lock:
            if sandbox_id not in self._sb:
                return False
            del self._sb[sandbox_id]
            self._msgs = [m for m in self._msgs
                          if m.sandbox_id != sandbox_id]
            return True

    def add_message(self, msg: ChatMessage) -> ChatMessage:
        if msg.message_id == "auto":
            msg.message_id = uuid.uuid4().hex
        with self._lock:
            self._msgs.append(msg)
            if msg.sandbox_id in self._sb:
                self._sb[msg.sandbox_id].last_active_at = msg.created_at
        return msg

    def list_messages(self, sandbox_id: str, *,
                       limit: int = 200,
                       after_message_id: str | None = None
                       ) -> list[ChatMessage]:
        with self._lock:
            items = [m for m in self._msgs
                     if m.sandbox_id == sandbox_id]
        items.sort(key=lambda m: m.created_at)
        if after_message_id:
            idx = next((i for i, m in enumerate(items)
                        if m.message_id == after_message_id), -1)
            items = items[idx + 1:]
        if limit:
            items = items[-limit:]
        return items

    # ---- groups ----
    def create_group(self, group: SandboxGroup) -> SandboxGroup:
        if group.group_id == "auto":
            group.group_id = uuid.uuid4().hex
        with self._lock:
            self._groups[group.group_id] = group
        return group

    def get_group(self, group_id: str) -> SandboxGroup | None:
        return self._groups.get(group_id)

    def list_groups(self, workspace_id: str) -> list[SandboxGroup]:
        with self._lock:
            items = [g for g in self._groups.values()
                     if g.workspace_id == workspace_id]
        return sorted(items, key=lambda g: g.created_at)

    def rename_group(self, group_id: str, name: str) -> SandboxGroup | None:
        with self._lock:
            g = self._groups.get(group_id)
            if not g:
                return None
            g.name = name
            return g

    def delete_group(self, group_id: str) -> bool:
        """删分组:把其下 sandbox 解绑(group_id=None),不删任务。"""
        with self._lock:
            if group_id not in self._groups:
                return False
            del self._groups[group_id]
            for sb in self._sb.values():
                if sb.group_id == group_id:
                    sb.group_id = None
            return True


def make_sandbox_store(dsn: str | None, *, eager_init: bool = True):
    if not dsn:
        return InMemorySandboxStore()
    parsed = urlparse(dsn)
    scheme = (parsed.scheme or "").lower()
    if len(scheme) == 1 and scheme.isalpha():
        scheme = ""
    if scheme in ("postgresql", "postgres"):
        from wanxiang.api.sandbox_store_pg import PgSandboxStore
        return PgSandboxStore(dsn, eager_init=eager_init)
    if scheme == "sqlite":
        path = parsed.path or dsn[len("sqlite:"):]
        if path.startswith("/") and len(path) > 2 and path[2] == ":":
            path = path[1:]
        from wanxiang.api.sandbox_store_sqlite import SqliteSandboxStore
        return SqliteSandboxStore(path)
    if not scheme:
        from wanxiang.api.sandbox_store_sqlite import SqliteSandboxStore
        return SqliteSandboxStore(dsn)
    raise ValueError(f"unsupported sandbox store DSN scheme: {scheme!r}")


__all__ = [
    "Sandbox", "SandboxGroup", "ChatMessage",
    "InMemorySandboxStore", "make_sandbox_store",
]
