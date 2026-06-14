# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""API key 鉴权 + 多租户 + 简单 RPM token bucket（M3-3 MVP）。

后续可替换为 Redis-backed store / DB-backed tenant 表。"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True)
class TenantInfo:
    tenant_id: str
    api_key: str
    rpm_limit: int = 60
    monthly_budget: int = 0  # 0 = unlimited (informational only)
    # spec D3: 租户级默认模型配置；当请求未显式指定 model 时回落到此。
    # 形如 ``{"provider": "deepseek", "model": "deepseek-chat", ...}``。
    default_model_config: dict | None = None

    def __hash__(self) -> int:  # dict 不可哈希；用 api_key 即可保证唯一
        return hash(self.api_key)


def resolve_effective_model(req_model, tenant: "TenantInfo | None"):
    """spec D3 模型解析策略（请求 > 租户默认 > stub 回落）。

    Args:
        req_model: 请求里携带的 ModelConfig（pydantic 模型）或 None。
        tenant: 当前请求归属的 TenantInfo；None 表示无租户上下文。

    Returns:
        一个非空的 ModelConfig 实例。

    优先级：
        1. 请求显式带了 ``model`` → 直接用（请求 wins）。
        2. 否则且 tenant.default_model_config 不空 → 用之构造 ModelConfig。
        3. 否则 → 回落 ``ModelConfig(provider="stub")``。
    """
    from wanxiang.api.schemas import ModelConfig  # 局部导入避免循环
    if req_model is not None:
        return req_model
    if tenant is not None and tenant.default_model_config:
        return ModelConfig(**tenant.default_model_config)
    return ModelConfig(provider="stub")


class TokenBucket:
    """经典 token bucket 限流器，in-memory，stdlib-only。

    容量 = rpm，refill 速率 = rpm / 60 tokens/sec。突发可一次吃满 rpm 个
    请求；连续打满后每秒回 1 token（rpm=60 时）。线程安全。
    """

    def __init__(self, rpm: int):
        if rpm < 1:
            raise ValueError("rpm must be >= 1")
        self.rpm = rpm
        self._capacity = float(rpm)
        self._refill_per_sec = rpm / 60.0
        self._tokens = float(rpm)
        self._last_refill = time.monotonic()
        self._lock = Lock()

    def _refill_locked(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        if elapsed > 0:
            self._tokens = min(self._capacity,
                               self._tokens + elapsed * self._refill_per_sec)
            self._last_refill = now

    def consume(self) -> bool:
        with self._lock:
            self._refill_locked()
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return True
            return False

    def retry_after_seconds(self) -> int:
        """估算下一个 token 可用还要等几秒（至少 1 秒，向上取整）。"""
        with self._lock:
            self._refill_locked()
            if self._tokens >= 1.0:
                return 1
            need = 1.0 - self._tokens
            seconds = need / self._refill_per_sec
            return max(1, int(seconds) if seconds == int(seconds)
                       else int(seconds) + 1)


class TenantStore:
    """In-memory tenant store keyed by api_key."""

    def __init__(self, tenants: list[TenantInfo]):
        self._by_key: dict[str, TenantInfo] = {t.api_key: t for t in tenants}
        self._buckets: dict[str, TokenBucket] = {
            t.tenant_id: TokenBucket(t.rpm_limit) for t in tenants}

    def lookup(self, api_key: str) -> TenantInfo | None:
        return self._by_key.get(api_key)

    def bucket_for(self, tenant_id: str) -> TokenBucket | None:
        return self._buckets.get(tenant_id)

    @classmethod
    def default(cls) -> "TenantStore":
        return cls([TenantInfo(tenant_id="demo", api_key="demo-key",
                                rpm_limit=60)])

    @classmethod
    def from_env(cls) -> "TenantStore":
        raw = os.environ.get("WANXIANG_TENANTS_JSON")
        if not raw:
            return cls.default()
        items = json.loads(raw)
        tenants = [
            TenantInfo(
                tenant_id=item["tenant_id"],
                api_key=item["api_key"],
                rpm_limit=int(item.get("rpm_limit", 60)),
                monthly_budget=int(item.get("monthly_budget", 0)),
                default_model_config=item.get("default_model_config"),
            )
            for item in items
        ]
        return cls(tenants)
