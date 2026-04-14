"""Platform adapters for Chinese social media platforms.

Usage:
    from engine.platforms import PlatformRegistry

    registry = PlatformRegistry()
    registry.auto_discover()
    platform = registry.create_platform("weibo", db_path="weibo.db")
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Any

from oasis.social_platform.platform import Platform


@dataclass
class PlatformConfig:
    """Configuration for a registered platform adapter."""

    name: str
    adapter_class: type[Platform]
    default_recsys: str = "random"
    default_actions: list[str] = field(default_factory=list)
    description: str = ""
    language: str = "zh-CN"


class PlatformRegistry:
    """Central registry for all platform adapters."""

    def __init__(self) -> None:
        self._platforms: dict[str, PlatformConfig] = {}

    def register(
        self,
        name: str,
        adapter_class: type[Platform],
        default_recsys: str = "random",
        default_actions: list[str] | None = None,
        description: str = "",
        language: str = "zh-CN",
    ) -> None:
        if name in self._platforms:
            raise ValueError(
                f"Platform '{name}' is already registered. "
                f"Use a different name or unregister first."
            )
        self._platforms[name] = PlatformConfig(
            name=name,
            adapter_class=adapter_class,
            default_recsys=default_recsys,
            default_actions=default_actions or [],
            description=description,
            language=language,
        )

    def unregister(self, name: str) -> None:
        if name not in self._platforms:
            raise KeyError(f"Platform '{name}' is not registered.")
        del self._platforms[name]

    def get(self, name: str) -> PlatformConfig:
        if name not in self._platforms:
            raise KeyError(
                f"Platform '{name}' is not registered. "
                f"Available: {', '.join(self._platforms.keys())}"
            )
        return self._platforms[name]

    def list_platforms(self) -> list[str]:
        return sorted(self._platforms.keys())

    def create_platform(
        self,
        name: str,
        db_path: str,
        channel: Any = None,
        **kwargs: Any,
    ) -> Platform:
        config = self.get(name)
        adapter_cls = config.adapter_class
        if "recsys_type" not in kwargs:
            kwargs["recsys_type"] = config.default_recsys
        return adapter_cls(db_path=db_path, channel=channel, **kwargs)

    def auto_discover(self) -> None:
        adapter_modules = [
            "engine.platforms.weibo",
            "engine.platforms.xiaohongshu",
            "engine.platforms.douyin",
            "engine.platforms.kuaishou",
            "engine.platforms.bilibili",
            "engine.platforms.wechat_video",
        ]
        for module_name in adapter_modules:
            try:
                importlib.import_module(module_name)
            except ImportError:
                pass


# Global registry instance
registry = PlatformRegistry()

# Register the two built-in OASIS platforms
registry.register(
    name="twitter",
    adapter_class=Platform,
    default_recsys="twitter",
    default_actions=[
        "create_post", "like_post", "repost",
        "follow", "do_nothing", "quote_post",
    ],
    description="Twitter-like microblogging platform (OASIS built-in)",
    language="en",
)

registry.register(
    name="reddit",
    adapter_class=Platform,
    default_recsys="reddit",
    default_actions=[
        "like_post", "dislike_post", "create_post",
        "create_comment", "like_comment", "dislike_comment",
        "search_posts", "search_user", "trend",
        "refresh", "do_nothing", "follow", "mute",
    ],
    description="Reddit-like forum platform (OASIS built-in)",
    language="en",
)
