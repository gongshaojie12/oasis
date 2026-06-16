# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""API keys bound to a workspace (P3).

Programmatic clients (curl, CI scripts) use the ``X-API-Key`` header.
Web users use Bearer JWT. Both ultimately resolve to a ``Workspace``.

Stores follow the same DSN-dispatch pattern as ``users.py`` /
``workspaces.py``: ``None`` -> in-memory; plain path / ``sqlite://`` ->
SQLite; ``postgresql://`` -> PG.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Literal
from urllib.parse import urlparse


@dataclass
class ApiKey:
    key_id: str
    workspace_id: str
    api_key: str  # the actual secret; MVP keeps plain (like "demo-key")
    name: str  # human label, e.g. "CI runner"
    role: Literal["admin", "member"] = "member"
    rpm_limit: int = 60
    monthly_budget: int | None = None
    created_by_user_id: str | None = None
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc))
    revoked_at: datetime | None = None


class InMemoryApiKeyStore:
    def __init__(self):
        self._by_key: dict[str, ApiKey] = {}
        self._by_id: dict[str, ApiKey] = {}
        self._lock = Lock()

    def create(self, ak: ApiKey) -> ApiKey:
        if ak.key_id == "auto":
            ak.key_id = uuid.uuid4().hex
        with self._lock:
            if ak.api_key in self._by_key:
                raise ValueError(f"api_key collision: {ak.api_key}")
            self._by_key[ak.api_key] = ak
            self._by_id[ak.key_id] = ak
        return ak

    def lookup(self, api_key: str) -> ApiKey | None:
        ak = self._by_key.get(api_key)
        if ak and ak.revoked_at is None:
            return ak
        return None

    def list_for_workspace(self, workspace_id: str) -> list[ApiKey]:
        with self._lock:
            return [
                k for k in self._by_id.values()
                if k.workspace_id == workspace_id and k.revoked_at is None
            ]

    def revoke(self, key_id: str) -> bool:
        with self._lock:
            ak = self._by_id.get(key_id)
            if not ak or ak.revoked_at is not None:
                return False
            ak.revoked_at = datetime.now(timezone.utc)
            return True


def make_api_key_store(dsn: str | None, *, eager_init: bool = True):
    if not dsn:
        return InMemoryApiKeyStore()
    parsed = urlparse(dsn)
    scheme = (parsed.scheme or "").lower()
    if len(scheme) == 1 and scheme.isalpha():
        scheme = ""
    if scheme in ("postgresql", "postgres"):
        from wanxiang.api.api_key_store_pg import PgApiKeyStore
        return PgApiKeyStore(dsn, eager_init=eager_init)
    if scheme == "sqlite":
        path = parsed.path or dsn[len("sqlite:"):]
        if path.startswith("/") and len(path) > 2 and path[2] == ":":
            path = path[1:]
        from wanxiang.api.api_key_store_sqlite import SqliteApiKeyStore
        return SqliteApiKeyStore(path)
    if not scheme:
        from wanxiang.api.api_key_store_sqlite import SqliteApiKeyStore
        return SqliteApiKeyStore(dsn)
    raise ValueError(f"unsupported api_key store DSN scheme: {scheme!r}")


__all__ = ["ApiKey", "InMemoryApiKeyStore", "make_api_key_store"]
