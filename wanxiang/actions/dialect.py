# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""L3 平台方言：把 L2 抽象动作映射为具体平台的形态。

每个平台是一份声明式 yaml（spec §5.4）。加载时校验所有声明的动作
都是已知的 L2 抽象动作，把国内外差异收敛为配置而非代码。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import yaml

from wanxiang.actions.l2_social import l2_action_names

_VALID_RELATIONSHIPS = {"weak", "none", "strong"}
_VALID_FEEDS = {"recommend", "following", "hotscore"}


@dataclass
class PlatformDialect:
    name: str
    display_name: str
    relationship: str
    feed_algorithm: str
    # 抽象动作名 -> {"alias": str, "extra": dict}
    supported: dict[str, dict[str, Any]] = field(default_factory=dict)

    def supports(self, action: str) -> bool:
        return action in self.supported

    def supported_action_names(self) -> set[str]:
        return set(self.supported.keys())

    def alias_of(self, action: str) -> str:
        if action not in self.supported:
            raise KeyError(f"action {action!r} not supported on {self.name}")
        return self.supported[action]["alias"]

    def extra_of(self, action: str) -> dict[str, Any]:
        if action not in self.supported:
            raise KeyError(f"action {action!r} not supported on {self.name}")
        return self.supported[action].get("extra", {})


class DialectLoader:
    """从目录加载平台方言 yaml。"""

    def __init__(self, dialect_dir: str):
        self.dialect_dir = dialect_dir

    def load(self, platform: str) -> PlatformDialect:
        path = os.path.join(self.dialect_dir, f"{platform}.yaml")
        if not os.path.exists(path):
            raise FileNotFoundError(f"dialect not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        return self._build(raw)

    def _build(self, raw: dict[str, Any]) -> PlatformDialect:
        relationship = raw["relationship"]
        if relationship not in _VALID_RELATIONSHIPS:
            raise ValueError(
                f"invalid relationship {relationship!r}; "
                f"expected one of {_VALID_RELATIONSHIPS}")
        feed = raw["feed_algorithm"]
        if feed not in _VALID_FEEDS:
            raise ValueError(
                f"invalid feed_algorithm {feed!r}; expected one of {_VALID_FEEDS}")

        known = l2_action_names()
        supported: dict[str, dict[str, Any]] = {}
        for action, cfg in (raw.get("supported_actions") or {}).items():
            if action not in known:
                raise ValueError(
                    f"{action!r} is not a known L2 action; "
                    f"valid actions: {sorted(known)}")
            cfg = cfg or {}
            supported[action] = {
                "alias": cfg.get("alias", action),
                "extra": cfg.get("extra", {}) or {},
            }

        # disabled_actions 校验：必须是已知 L2 动作，且不能同时出现在 supported
        for action in (raw.get("disabled_actions") or []):
            if action not in known:
                raise ValueError(
                    f"disabled action {action!r} is not a known L2 action")
            supported.pop(action, None)

        return PlatformDialect(
            name=raw["name"],
            display_name=raw["display_name"],
            relationship=relationship,
            feed_algorithm=feed,
            supported=supported,
        )
