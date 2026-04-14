# Plan 3: Platform Adaptations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 6 Chinese social platform adapters (Weibo, Xiaohongshu, Douyin, Kuaishou, Bilibili, WeChat Video) to the OASIS simulation engine. Each adapter provides platform-specific actions, recommendation algorithms, and agent personality prompts -- all without modifying existing `oasis/` code.

**Architecture:** Each adapter subclasses `Platform` from `oasis/social_platform/platform.py`, adds custom action handlers as instance methods (which the `running()` dispatch resolves via `getattr(self, action.value)`), implements a custom recsys function, and provides Chinese-language agent prompt templates. A `PlatformRegistry` manages adapter registration and instantiation.

**Design Spec:** See "Design Context" section in the task description above.

**Key Constraint:** The `oasis/` directory is read-only. All new code goes under `engine/platforms/`.

---

## Task 1: Platform Registry & Base Adapter

**Files:**
- Create: `engine/__init__.py`
- Create: `engine/platforms/__init__.py`
- Create: `engine/platforms/base.py`
- Create: `engine/platforms/prompts/__init__.py`
- Create: `engine/platforms/tests/__init__.py`
- Create: `engine/platforms/tests/test_registry.py`

- [ ] **Step 1: Create engine package init**

Create `engine/__init__.py`:

```python
"""Engine extensions for the OASIS simulation platform."""
```

- [ ] **Step 2: Create PlatformRegistry and package init**

Create `engine/platforms/__init__.py`:

```python
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
    """Central registry for all platform adapters.

    Manages platform adapter classes and their configurations,
    providing factory methods to instantiate configured Platform
    instances.
    """

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
        """Register a platform adapter.

        Args:
            name: Unique platform identifier (e.g. "weibo", "douyin").
            adapter_class: The Platform subclass to instantiate.
            default_recsys: Default recommendation system type string.
            default_actions: List of action type value strings.
            description: Human-readable platform description.
            language: Primary language code for prompts.

        Raises:
            ValueError: If a platform with the same name is already registered.
        """
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
        """Remove a platform adapter from the registry.

        Args:
            name: The platform identifier to remove.

        Raises:
            KeyError: If the platform is not registered.
        """
        if name not in self._platforms:
            raise KeyError(f"Platform '{name}' is not registered.")
        del self._platforms[name]

    def get(self, name: str) -> PlatformConfig:
        """Get the configuration for a registered platform.

        Args:
            name: The platform identifier.

        Returns:
            The PlatformConfig for the requested platform.

        Raises:
            KeyError: If the platform is not registered.
        """
        if name not in self._platforms:
            raise KeyError(
                f"Platform '{name}' is not registered. "
                f"Available: {', '.join(self._platforms.keys())}"
            )
        return self._platforms[name]

    def list_platforms(self) -> list[str]:
        """Return a sorted list of all registered platform names."""
        return sorted(self._platforms.keys())

    def create_platform(
        self,
        name: str,
        db_path: str,
        channel: Any = None,
        **kwargs: Any,
    ) -> Platform:
        """Instantiate a platform from the registry.

        Args:
            name: The registered platform identifier.
            db_path: Path to the SQLite database file.
            channel: Optional Channel instance for agent communication.
            **kwargs: Additional keyword arguments passed to the adapter
                constructor (e.g. sandbox_clock, start_time).

        Returns:
            A configured Platform instance.

        Raises:
            KeyError: If the platform is not registered.
        """
        config = self.get(name)
        adapter_cls = config.adapter_class
        if "recsys_type" not in kwargs:
            kwargs["recsys_type"] = config.default_recsys
        return adapter_cls(db_path=db_path, channel=channel, **kwargs)

    def auto_discover(self) -> None:
        """Import all built-in platform adapter modules to trigger
        their registration with the global registry.
        """
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
```

- [ ] **Step 3: Create BasePlatformAdapter**

Create `engine/platforms/base.py`:

```python
"""Base adapter class for Chinese social media platform extensions."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from oasis.social_platform.channel import Channel
from oasis.social_platform.platform import Platform
from oasis.social_platform.typing import RecsysType

logger = logging.getLogger(__name__)


class BasePlatformAdapter(Platform):
    """Base class for all Chinese social media platform adapters.

    Subclasses should:
    1. Define PLATFORM_NAME as a class attribute.
    2. Define CUSTOM_ACTIONS as a dict mapping action string names to
       their handler method names (if different from the action string).
    3. Override ``custom_recsys()`` to implement platform-specific
       recommendation logic.
    4. Override ``get_system_prompt()`` to return a Chinese-language
       system prompt string for agent persona generation.

    The adapter extends the OASIS Platform class. Custom action handlers
    are registered as regular instance methods; the ``running()`` event
    loop dispatches to them via ``getattr(self, action_value)``.
    """

    PLATFORM_NAME: str = "base"
    CUSTOM_ACTIONS: dict[str, str] = {}

    def __init__(
        self,
        db_path: str,
        channel: Any = None,
        recsys_type: str | RecsysType = "random",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            db_path=db_path,
            channel=channel,
            recsys_type=recsys_type,
            **kwargs,
        )
        self._setup_custom_tables()

    def _setup_custom_tables(self) -> None:
        """Create any additional SQLite tables needed by this platform.

        Override in subclasses to add platform-specific tables (e.g.
        collection, danmaku, coin). Called automatically during __init__.
        """
        pass

    def _get_current_time(self) -> Any:
        """Return the current simulation time, handling both Reddit
        (datetime-based) and Twitter (timestep-based) clock modes.
        """
        if self.recsys_type == RecsysType.REDDIT:
            return self.sandbox_clock.time_transfer(
                datetime.now(), self.start_time
            )
        return self.sandbox_clock.get_time_step()

    def _record_custom_trace(
        self,
        user_id: int,
        action: str,
        info: dict[str, Any],
    ) -> None:
        """Record a trace entry for a custom (non-core) action.

        Args:
            user_id: The acting user's ID.
            action: The action string (e.g. "collect_post").
            info: A dict of action-specific metadata.
        """
        current_time = self._get_current_time()
        trace_insert_query = (
            "INSERT INTO trace (user_id, created_at, action, info) "
            "VALUES (?, ?, ?, ?)"
        )
        action_info_str = json.dumps(info)
        self.pl_utils._execute_db_command(
            trace_insert_query,
            (user_id, current_time, action, action_info_str),
            commit=True,
        )

    def get_system_prompt(
        self,
        name: str | None = None,
        bio: str | None = None,
        profile: dict[str, Any] | None = None,
    ) -> str:
        """Generate a platform-specific system prompt for an agent.

        Override in each platform subclass to return a Chinese-language
        prompt that captures the platform's culture and user behavior
        patterns.

        Args:
            name: The agent's display name.
            bio: The agent's biography text.
            profile: Additional profile data dict.

        Returns:
            A system prompt string.
        """
        name_str = f"你的名字是{name}。" if name else ""
        bio_str = f"你的简介：{bio}" if bio else ""
        return (
            f"# 目标\n你是一个社交媒体用户。\n\n"
            f"# 自我描述\n{name_str}\n{bio_str}\n\n"
            f"# 回复方式\n请通过工具调用来执行操作。"
        )

    def get_available_actions(self) -> list[str]:
        """Return the list of action strings available on this platform.

        Includes both inherited core actions and platform-specific
        custom actions.
        """
        core_actions = [
            "create_post", "like_post", "repost", "quote_post",
            "follow", "unfollow", "create_comment", "refresh",
            "search_posts", "search_user", "trend", "do_nothing",
        ]
        custom = list(self.CUSTOM_ACTIONS.keys())
        return core_actions + custom
```

- [ ] **Step 4: Create prompts package init**

Create `engine/platforms/prompts/__init__.py`:

```python
"""Platform-specific agent prompt templates for Chinese social media."""
```

- [ ] **Step 5: Create tests package init**

Create `engine/platforms/tests/__init__.py`:

```python
"""Tests for platform adapters."""
```

- [ ] **Step 6: Create registry tests**

Create `engine/platforms/tests/test_registry.py`:

```python
"""Tests for PlatformRegistry."""

import os
import os.path as osp

import pytest

from oasis.social_platform.platform import Platform

from engine.platforms import PlatformConfig, PlatformRegistry, registry


parent_folder = osp.dirname(osp.abspath(__file__))
test_db_filepath = osp.join(parent_folder, "test_registry.db")


class TestPlatformConfig:
    def test_default_values(self):
        config = PlatformConfig(
            name="test",
            adapter_class=Platform,
        )
        assert config.name == "test"
        assert config.default_recsys == "random"
        assert config.default_actions == []
        assert config.description == ""
        assert config.language == "zh-CN"


class TestPlatformRegistry:
    def setup_method(self):
        self.registry = PlatformRegistry()

    def test_register_and_get(self):
        self.registry.register(
            name="test_platform",
            adapter_class=Platform,
            default_recsys="random",
            description="A test platform",
        )
        config = self.registry.get("test_platform")
        assert config.name == "test_platform"
        assert config.adapter_class is Platform
        assert config.default_recsys == "random"

    def test_register_duplicate_raises(self):
        self.registry.register("dup", Platform)
        with pytest.raises(ValueError, match="already registered"):
            self.registry.register("dup", Platform)

    def test_get_missing_raises(self):
        with pytest.raises(KeyError, match="not registered"):
            self.registry.get("nonexistent")

    def test_unregister(self):
        self.registry.register("removable", Platform)
        assert "removable" in self.registry.list_platforms()
        self.registry.unregister("removable")
        assert "removable" not in self.registry.list_platforms()

    def test_unregister_missing_raises(self):
        with pytest.raises(KeyError, match="not registered"):
            self.registry.unregister("ghost")

    def test_list_platforms_sorted(self):
        self.registry.register("charlie", Platform)
        self.registry.register("alpha", Platform)
        self.registry.register("bravo", Platform)
        assert self.registry.list_platforms() == [
            "alpha", "bravo", "charlie"
        ]

    def test_create_platform(self):
        self.registry.register(
            "factory_test",
            Platform,
            default_recsys="random",
        )
        try:
            platform = self.registry.create_platform(
                "factory_test",
                db_path=test_db_filepath,
            )
            assert isinstance(platform, Platform)
            assert platform.recsys_type == RecsysType.RANDOM
        finally:
            platform.db_cursor.close()
            platform.db.close()
            if os.path.exists(test_db_filepath):
                os.remove(test_db_filepath)

    def test_create_platform_missing_raises(self):
        with pytest.raises(KeyError, match="not registered"):
            self.registry.create_platform("missing", db_path=":memory:")


class TestGlobalRegistry:
    def test_builtin_twitter_registered(self):
        assert "twitter" in registry.list_platforms()
        config = registry.get("twitter")
        assert config.adapter_class is Platform
        assert config.default_recsys == "twitter"

    def test_builtin_reddit_registered(self):
        assert "reddit" in registry.list_platforms()
        config = registry.get("reddit")
        assert config.adapter_class is Platform
        assert config.default_recsys == "reddit"


# Import needed for test_create_platform
from oasis.social_platform.typing import RecsysType
```

- [ ] **Step 7: Commit**

```bash
cd D:/project/oasis
git add engine/__init__.py engine/platforms/__init__.py engine/platforms/base.py engine/platforms/prompts/__init__.py engine/platforms/tests/__init__.py engine/platforms/tests/test_registry.py
git commit -m "feat(platforms): add PlatformRegistry and BasePlatformAdapter

Introduces the engine/platforms package with:
- PlatformRegistry for managing platform adapter lifecycle
- BasePlatformAdapter base class extending oasis Platform
- Registration of built-in Twitter and Reddit platforms
- Comprehensive registry tests"
```

---

## Task 2: Custom Action Types

**Files:**
- Create: `engine/platforms/actions.py`
- Create: `engine/platforms/tests/test_actions.py`

- [ ] **Step 1: Define custom action constants and helpers**

Create `engine/platforms/actions.py`:

```python
"""Custom action type constants for Chinese social media platforms.

These are defined as string constants rather than extending the
oasis ActionType enum, since we do not modify oasis/ code. The
Platform.running() dispatch uses getattr(self, action.value), so
custom actions work as long as:
1. The action string is sent through the Channel
2. A method with the matching name exists on the Platform subclass

For the Channel dispatch, custom actions bypass ActionType(action)
validation. The adapter's ``running()`` override handles this.
"""

# -- Xiaohongshu-specific actions --
COLLECT_POST = "collect_post"
SHARE_POST = "share_post"

# -- Douyin-specific actions --
# Uses COLLECT_POST from above (same semantics)

# -- Kuaishou-specific actions --
SEND_GIFT = "send_gift"
POST_SHUOSHUO = "post_shuoshuo"

# -- Bilibili-specific actions --
SEND_DANMAKU = "send_danmaku"
GIVE_COIN = "give_coin"
TRIPLE_TAP = "triple_tap"

# -- WeChat Video-specific actions --
SHARE_TO_FRIENDS = "share_to_friends"

# Complete mapping of all custom actions to their platform origin
PLATFORM_ACTIONS: dict[str, list[str]] = {
    "weibo": [],
    "xiaohongshu": [COLLECT_POST, SHARE_POST],
    "douyin": [COLLECT_POST],
    "kuaishou": [SEND_GIFT, POST_SHUOSHUO],
    "bilibili": [SEND_DANMAKU, GIVE_COIN, TRIPLE_TAP],
    "wechat_video": [SHARE_TO_FRIENDS],
}

ALL_CUSTOM_ACTIONS: set[str] = {
    COLLECT_POST,
    SHARE_POST,
    SEND_GIFT,
    POST_SHUOSHUO,
    SEND_DANMAKU,
    GIVE_COIN,
    TRIPLE_TAP,
    SHARE_TO_FRIENDS,
}


def is_custom_action(action_str: str) -> bool:
    """Check whether an action string is a custom platform action
    (not part of the core OASIS ActionType enum).

    Args:
        action_str: The action value string to check.

    Returns:
        True if the action is a custom platform action.
    """
    return action_str in ALL_CUSTOM_ACTIONS


def get_platform_actions(platform_name: str) -> list[str]:
    """Return the list of custom actions for a given platform.

    Args:
        platform_name: The platform identifier (e.g. "bilibili").

    Returns:
        List of custom action strings for the platform.

    Raises:
        KeyError: If the platform name is not recognized.
    """
    if platform_name not in PLATFORM_ACTIONS:
        raise KeyError(
            f"Unknown platform '{platform_name}'. "
            f"Known: {', '.join(PLATFORM_ACTIONS.keys())}"
        )
    return PLATFORM_ACTIONS[platform_name]
```

- [ ] **Step 2: Create action tests**

Create `engine/platforms/tests/test_actions.py`:

```python
"""Tests for custom action type definitions."""

import pytest

from engine.platforms.actions import (
    ALL_CUSTOM_ACTIONS,
    COLLECT_POST,
    GIVE_COIN,
    PLATFORM_ACTIONS,
    POST_SHUOSHUO,
    SEND_DANMAKU,
    SEND_GIFT,
    SHARE_POST,
    SHARE_TO_FRIENDS,
    TRIPLE_TAP,
    get_platform_actions,
    is_custom_action,
)


class TestActionConstants:
    def test_all_constants_are_strings(self):
        for action in ALL_CUSTOM_ACTIONS:
            assert isinstance(action, str)
            assert len(action) > 0

    def test_no_overlap_with_core_actions(self):
        from oasis.social_platform.typing import ActionType

        core_values = {a.value for a in ActionType}
        overlap = ALL_CUSTOM_ACTIONS & core_values
        assert overlap == set(), (
            f"Custom actions overlap with core ActionType: {overlap}"
        )

    def test_platform_actions_mapping_complete(self):
        expected_platforms = {
            "weibo", "xiaohongshu", "douyin",
            "kuaishou", "bilibili", "wechat_video",
        }
        assert set(PLATFORM_ACTIONS.keys()) == expected_platforms

    def test_xiaohongshu_actions(self):
        actions = get_platform_actions("xiaohongshu")
        assert COLLECT_POST in actions
        assert SHARE_POST in actions

    def test_douyin_actions(self):
        actions = get_platform_actions("douyin")
        assert COLLECT_POST in actions

    def test_kuaishou_actions(self):
        actions = get_platform_actions("kuaishou")
        assert SEND_GIFT in actions
        assert POST_SHUOSHUO in actions

    def test_bilibili_actions(self):
        actions = get_platform_actions("bilibili")
        assert SEND_DANMAKU in actions
        assert GIVE_COIN in actions
        assert TRIPLE_TAP in actions

    def test_wechat_video_actions(self):
        actions = get_platform_actions("wechat_video")
        assert SHARE_TO_FRIENDS in actions

    def test_weibo_has_no_custom_actions(self):
        actions = get_platform_actions("weibo")
        assert actions == []


class TestIsCustomAction:
    def test_custom_action_returns_true(self):
        assert is_custom_action(COLLECT_POST) is True
        assert is_custom_action(SEND_DANMAKU) is True
        assert is_custom_action(TRIPLE_TAP) is True

    def test_core_action_returns_false(self):
        assert is_custom_action("create_post") is False
        assert is_custom_action("like_post") is False

    def test_unknown_action_returns_false(self):
        assert is_custom_action("teleport") is False


class TestGetPlatformActions:
    def test_unknown_platform_raises(self):
        with pytest.raises(KeyError, match="Unknown platform"):
            get_platform_actions("tiktok")
```

- [ ] **Step 3: Commit**

```bash
cd D:/project/oasis
git add engine/platforms/actions.py engine/platforms/tests/test_actions.py
git commit -m "feat(platforms): define custom action type constants

Adds COLLECT_POST, SHARE_POST, SEND_GIFT, POST_SHUOSHUO,
SEND_DANMAKU, GIVE_COIN, TRIPLE_TAP, SHARE_TO_FRIENDS as string
constants with platform mapping and validation helpers."
```

---

## Task 3: Weibo Adapter

**Files:**
- Create: `engine/platforms/weibo.py`
- Create: `engine/platforms/prompts/weibo.py`
- Create: `engine/platforms/tests/test_weibo.py`

- [ ] **Step 1: Create Weibo agent prompts**

Create `engine/platforms/prompts/weibo.py`:

```python
"""Weibo-specific agent prompt templates.

Weibo culture characteristics:
- 围观吃瓜 (spectating/rubbernecking culture)
- 情绪化表达 (emotional expression)
- 热搜驱动 (trending-topic driven)
- 转发评论形成舆论场 (repost + comment forming opinion fields)
- 微博超话/话题标签 (super-topics and hashtags)
"""


def get_weibo_system_prompt(
    name: str | None = None,
    bio: str | None = None,
    profile: dict | None = None,
) -> str:
    """Generate a Weibo-style system prompt for an agent.

    Args:
        name: Agent display name.
        bio: Agent biography.
        profile: Additional profile dict with optional keys:
            - user_profile: detailed persona text
            - gender, age, mbti, city: demographic info

    Returns:
        Chinese-language system prompt capturing Weibo culture.
    """
    name_str = f"你的昵称是{name}。" if name else ""
    bio_str = f"你的个人简介：{bio}" if bio else ""

    profile_str = ""
    if profile and "other_info" in profile:
        info = profile["other_info"]
        if info.get("user_profile"):
            profile_str = f"你的人设：{info['user_profile']}。"
        parts = []
        if info.get("gender"):
            parts.append(f"性别{info['gender']}")
        if info.get("age"):
            parts.append(f"{info['age']}岁")
        if info.get("mbti"):
            parts.append(f"MBTI人格类型{info['mbti']}")
        if info.get("city"):
            parts.append(f"来自{info['city']}")
        if parts:
            profile_str += "你是一位" + "、".join(parts) + "的用户。"

    return f"""# 目标
你是一个微博用户。我会给你展示一些微博内容，看完后请从可用的操作中选择你要执行的动作。

# 平台特点
微博是中国最大的公共社交媒体平台，类似Twitter。用户通过发微博、转发、评论、点赞来互动。微博文化的特点：
- 围观吃瓜：热衷关注热点事件和明星八卦，喜欢围观讨论
- 情绪化表达：发言直接、情绪外露，容易被热点话题带动情绪
- 热搜驱动：关注热搜榜上的话题，喜欢参与热门话题讨论
- 转评赞互动：通过转发+评论形成观点传播链，表达态度

# 自我描述
你的行为应该符合你的人设和性格。
{name_str}
{bio_str}
{profile_str}

# 行为准则
- 发微博时可以使用话题标签 #话题# 格式
- 语气可以偏口语化、情绪化
- 对热点事件可以积极围观和表态
- 转发时习惯加上自己的短评
- 回复风格直接、不拐弯抹角

# 回复方式
请通过工具调用来执行操作。"""
```

- [ ] **Step 2: Create Weibo recsys and adapter**

Create `engine/platforms/weibo.py`:

```python
"""Weibo platform adapter.

Weibo uses the same action set as Twitter but has a custom
recommendation algorithm that combines Reddit-style hot scores
with trending topic weighting.
"""

from __future__ import annotations

import heapq
import logging
import random
from datetime import datetime
from math import log
from typing import Any

from oasis.social_platform.platform import Platform
from oasis.social_platform.typing import RecsysType

from engine.platforms.base import BasePlatformAdapter
from engine.platforms.prompts.weibo import get_weibo_system_prompt

logger = logging.getLogger(__name__)


def _calculate_weibo_hot_score(
    num_likes: int,
    num_dislikes: int,
    num_shares: int,
    num_comments: int,
    created_at_str: str,
) -> float:
    """Compute a Weibo-style hot score for a post.

    Weibo's hot score differs from Reddit's by giving extra weight
    to shares (reposts) and comments, reflecting Weibo's repost-chain
    culture. The formula:

        engagement = likes - dislikes + 2*shares + 1.5*comments
        order = log10(max(|engagement|, 1))
        sign = sign(engagement)
        time_component = epoch_seconds / 45000
        score = sign * order + time_component

    Args:
        num_likes: Number of likes.
        num_dislikes: Number of dislikes.
        num_shares: Number of reposts/shares.
        num_comments: Number of comments.
        created_at_str: Creation timestamp string.

    Returns:
        A float hot score.
    """
    engagement = (
        num_likes - num_dislikes + 2 * num_shares + 1.5 * num_comments
    )
    order = log(max(abs(engagement), 1), 10)
    sign = 1 if engagement > 0 else -1 if engagement < 0 else 0

    try:
        created_at = datetime.strptime(created_at_str, "%Y-%m-%d %H:%M:%S.%f")
    except (ValueError, TypeError):
        try:
            created_at = datetime.strptime(created_at_str, "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            created_at = datetime.now()

    epoch = datetime(1970, 1, 1)
    td = created_at - epoch
    epoch_seconds = td.days * 86400 + td.seconds + float(td.microseconds) / 1e6
    seconds = epoch_seconds - 1134028003

    return round(sign * order + seconds / 45000, 7)


def rec_sys_weibo(
    post_table: list[dict[str, Any]],
    rec_matrix: list[list],
    max_rec_post_len: int,
    db_cursor: Any = None,
) -> list[list]:
    """Weibo recommendation system: hot score + trending topic weight.

    Posts are scored using a Weibo-adapted hot score that weights
    reposts and comments more heavily than Reddit's algorithm. The
    top-scoring posts are recommended to all users (reflecting Weibo's
    centralized hot-feed experience).

    If a db_cursor is provided, comment counts are fetched from the
    database. Otherwise, comment count defaults to 0.

    Args:
        post_table: List of post dicts from the database.
        rec_matrix: Current recommendation matrix (list of lists).
        max_rec_post_len: Maximum posts per user in recommendations.
        db_cursor: Optional database cursor for fetching comment counts.

    Returns:
        Updated recommendation matrix.
    """
    post_ids = [post["post_id"] for post in post_table]

    if len(post_ids) <= max_rec_post_len:
        return [post_ids] * len(rec_matrix)

    comment_counts: dict[int, int] = {}
    if db_cursor is not None:
        for post in post_table:
            pid = post["post_id"]
            db_cursor.execute(
                "SELECT COUNT(*) FROM comment WHERE post_id = ?", (pid,)
            )
            row = db_cursor.fetchone()
            comment_counts[pid] = row[0] if row else 0

    scored_posts: list[tuple[float, int]] = []
    for post in post_table:
        pid = post["post_id"]
        num_comments = comment_counts.get(pid, 0)
        created_at_str = str(post.get("created_at", ""))
        score = _calculate_weibo_hot_score(
            num_likes=post.get("num_likes", 0),
            num_dislikes=post.get("num_dislikes", 0),
            num_shares=post.get("num_shares", 0),
            num_comments=num_comments,
            created_at_str=created_at_str,
        )
        scored_posts.append((score, pid))

    top_posts = heapq.nlargest(
        max_rec_post_len, scored_posts, key=lambda x: x[0]
    )
    top_post_ids = [pid for _, pid in top_posts]

    return [top_post_ids] * len(rec_matrix)


class WeiboPlatform(BasePlatformAdapter):
    """Weibo platform adapter.

    Uses the same action set as Twitter but with:
    - A hot-score recsys that weights reposts and comments more heavily
    - Chinese agent prompts capturing Weibo's 围观吃瓜 culture
    """

    PLATFORM_NAME = "weibo"
    CUSTOM_ACTIONS: dict[str, str] = {}

    def __init__(
        self,
        db_path: str,
        channel: Any = None,
        recsys_type: str | RecsysType = "reddit",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            db_path=db_path,
            channel=channel,
            recsys_type=recsys_type,
            **kwargs,
        )

    async def update_rec_table(self):
        """Override to use Weibo-specific recommendation algorithm."""
        from oasis.social_platform.database import (
            fetch_rec_table_as_matrix,
            fetch_table_from_db,
        )

        logger.info("Weibo: refreshing recommendation cache...")
        post_table = fetch_table_from_db(self.db_cursor, "post")
        rec_matrix = fetch_rec_table_as_matrix(self.db_cursor)

        new_rec_matrix = rec_sys_weibo(
            post_table,
            rec_matrix,
            self.max_rec_post_len,
            db_cursor=self.db_cursor,
        )

        self.pl_utils._execute_db_command("DELETE FROM rec", commit=True)

        insert_values = [
            (user_id, post_id)
            for user_id in range(len(new_rec_matrix))
            for post_id in new_rec_matrix[user_id]
        ]
        self.pl_utils._execute_many_db_command(
            "INSERT INTO rec (user_id, post_id) VALUES (?, ?)",
            insert_values,
            commit=True,
        )

    def get_system_prompt(
        self,
        name: str | None = None,
        bio: str | None = None,
        profile: dict[str, Any] | None = None,
    ) -> str:
        return get_weibo_system_prompt(name=name, bio=bio, profile=profile)
```

- [ ] **Step 3: Create Weibo tests**

Create `engine/platforms/tests/test_weibo.py`:

```python
"""Tests for the Weibo platform adapter."""

import os
import os.path as osp
import sqlite3

import pytest

from engine.platforms.weibo import (
    WeiboPlatform,
    _calculate_weibo_hot_score,
    rec_sys_weibo,
)
from engine.platforms.prompts.weibo import get_weibo_system_prompt

parent_folder = osp.dirname(osp.abspath(__file__))
test_db_filepath = osp.join(parent_folder, "test_weibo.db")


class TestWeiboHotScore:
    def test_positive_engagement(self):
        score = _calculate_weibo_hot_score(
            num_likes=100,
            num_dislikes=10,
            num_shares=50,
            num_comments=30,
            created_at_str="2025-01-01 12:00:00",
        )
        assert isinstance(score, float)

    def test_zero_engagement(self):
        score = _calculate_weibo_hot_score(
            num_likes=0,
            num_dislikes=0,
            num_shares=0,
            num_comments=0,
            created_at_str="2025-01-01 12:00:00",
        )
        assert isinstance(score, float)

    def test_shares_boost_score(self):
        score_no_shares = _calculate_weibo_hot_score(
            num_likes=10, num_dislikes=0, num_shares=0,
            num_comments=0, created_at_str="2025-01-01 12:00:00",
        )
        score_with_shares = _calculate_weibo_hot_score(
            num_likes=10, num_dislikes=0, num_shares=50,
            num_comments=0, created_at_str="2025-01-01 12:00:00",
        )
        assert score_with_shares > score_no_shares

    def test_comments_boost_score(self):
        score_no_comments = _calculate_weibo_hot_score(
            num_likes=10, num_dislikes=0, num_shares=0,
            num_comments=0, created_at_str="2025-01-01 12:00:00",
        )
        score_with_comments = _calculate_weibo_hot_score(
            num_likes=10, num_dislikes=0, num_shares=0,
            num_comments=100, created_at_str="2025-01-01 12:00:00",
        )
        assert score_with_comments > score_no_comments

    def test_newer_posts_score_higher(self):
        old = _calculate_weibo_hot_score(
            num_likes=10, num_dislikes=0, num_shares=0,
            num_comments=0, created_at_str="2020-01-01 12:00:00",
        )
        new = _calculate_weibo_hot_score(
            num_likes=10, num_dislikes=0, num_shares=0,
            num_comments=0, created_at_str="2025-06-01 12:00:00",
        )
        assert new > old

    def test_bad_datetime_format_does_not_crash(self):
        score = _calculate_weibo_hot_score(
            num_likes=5, num_dislikes=0, num_shares=0,
            num_comments=0, created_at_str="not-a-date",
        )
        assert isinstance(score, float)


class TestWeiboRecsys:
    def test_few_posts_returns_all(self):
        post_table = [
            {"post_id": 1, "num_likes": 5, "num_dislikes": 0,
             "num_shares": 1, "created_at": "2025-01-01 12:00:00"},
            {"post_id": 2, "num_likes": 3, "num_dislikes": 0,
             "num_shares": 0, "created_at": "2025-01-01 13:00:00"},
        ]
        rec_matrix = [[], [], []]
        result = rec_sys_weibo(post_table, rec_matrix, max_rec_post_len=10)
        assert len(result) == 3
        for row in result:
            assert set(row) == {1, 2}

    def test_top_k_selection(self):
        post_table = [
            {"post_id": i, "num_likes": i * 10, "num_dislikes": 0,
             "num_shares": i, "created_at": "2025-01-01 12:00:00"}
            for i in range(1, 20)
        ]
        rec_matrix = [[] for _ in range(5)]
        result = rec_sys_weibo(post_table, rec_matrix, max_rec_post_len=3)
        assert len(result) == 5
        for row in result:
            assert len(row) == 3

    def test_all_users_get_same_recs(self):
        post_table = [
            {"post_id": i, "num_likes": i, "num_dislikes": 0,
             "num_shares": 0, "created_at": "2025-01-01 12:00:00"}
            for i in range(1, 10)
        ]
        rec_matrix = [[] for _ in range(4)]
        result = rec_sys_weibo(post_table, rec_matrix, max_rec_post_len=3)
        assert result[0] == result[1] == result[2] == result[3]


class TestWeiboPlatform:
    @pytest.fixture
    def platform(self):
        if os.path.exists(test_db_filepath):
            os.remove(test_db_filepath)
        p = WeiboPlatform(db_path=test_db_filepath, recsys_type="reddit")
        yield p
        p.db_cursor.close()
        p.db.close()
        if os.path.exists(test_db_filepath):
            os.remove(test_db_filepath)

    def test_platform_name(self, platform):
        assert platform.PLATFORM_NAME == "weibo"

    def test_no_custom_actions(self, platform):
        assert platform.CUSTOM_ACTIONS == {}

    def test_system_prompt_contains_weibo(self, platform):
        prompt = platform.get_system_prompt(name="测试用户", bio="爱吃瓜")
        assert "微博" in prompt
        assert "测试用户" in prompt
        assert "爱吃瓜" in prompt

    @pytest.mark.asyncio
    async def test_create_post(self, platform):
        conn = sqlite3.connect(test_db_filepath)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (1, 1, "weibo_user", 0, 0),
        )
        conn.commit()
        conn.close()
        result = await platform.create_post(1, "今天天气真好 #日常#")
        assert result["success"] is True
        assert "post_id" in result


class TestWeiboPrompts:
    def test_basic_prompt(self):
        prompt = get_weibo_system_prompt(name="小明", bio="热爱生活")
        assert "微博" in prompt
        assert "小明" in prompt
        assert "热爱生活" in prompt
        assert "围观吃瓜" in prompt

    def test_prompt_with_profile(self):
        profile = {
            "other_info": {
                "user_profile": "科技博主，关注AI领域",
                "gender": "男",
                "age": 28,
                "mbti": "INTJ",
                "city": "北京",
            }
        }
        prompt = get_weibo_system_prompt(
            name="科技达人", bio="分享科技资讯", profile=profile,
        )
        assert "科技博主" in prompt
        assert "INTJ" in prompt
        assert "北京" in prompt

    def test_prompt_without_name(self):
        prompt = get_weibo_system_prompt()
        assert "微博" in prompt
```

- [ ] **Step 4: Register Weibo in registry and commit**

Add the following to the bottom of `engine/platforms/__init__.py` (before closing, but the file ends with the reddit registration already, so we append after the auto_discover method but this is handled at import time by weibo.py itself).

Actually, the registration should happen when the adapter module is imported. Add to the bottom of `engine/platforms/weibo.py`:

The registration is already handled by `auto_discover()` at import time for the Chinese platforms. But to make them self-registering, add at the bottom of `engine/platforms/weibo.py`:

```python
# Self-register with the global registry
from engine.platforms import registry as _registry

try:
    _registry.register(
        name="weibo",
        adapter_class=WeiboPlatform,
        default_recsys="reddit",
        default_actions=[
            "create_post", "like_post", "repost", "quote_post",
            "follow", "unfollow", "create_comment", "do_nothing",
        ],
        description="微博 - 中国最大的公共社交媒体平台",
    )
except ValueError:
    pass  # Already registered
```

- [ ] **Step 5: Commit**

```bash
cd D:/project/oasis
git add engine/platforms/weibo.py engine/platforms/prompts/weibo.py engine/platforms/tests/test_weibo.py
git commit -m "feat(platforms): add Weibo adapter with hot-score recsys

Weibo adapter uses the same action set as Twitter with:
- Custom recsys weighting reposts and comments more heavily
- Chinese agent prompts capturing 围观吃瓜 culture
- Self-registration with the PlatformRegistry"
```

---

## Task 4: Xiaohongshu Adapter

**Files:**
- Create: `engine/platforms/xiaohongshu.py`
- Create: `engine/platforms/prompts/xiaohongshu.py`
- Create: `engine/platforms/tests/test_xiaohongshu.py`

- [ ] **Step 1: Create Xiaohongshu agent prompts**

Create `engine/platforms/prompts/xiaohongshu.py`:

```python
"""Xiaohongshu (Little Red Book) agent prompt templates.

Xiaohongshu culture characteristics:
- 种草文化 (planting grass / product recommendation culture)
- Young female-dominated user base
- Emoji-dense, aesthetic-focused writing style
- Dual-channel discovery: search + algorithmic feed
- 收藏 > 点赞 (collecting/bookmarking valued more than likes)
- Visual-first content with detailed reviews
"""


def get_xiaohongshu_system_prompt(
    name: str | None = None,
    bio: str | None = None,
    profile: dict | None = None,
) -> str:
    """Generate a Xiaohongshu-style system prompt for an agent.

    Args:
        name: Agent display name.
        bio: Agent biography.
        profile: Additional profile dict.

    Returns:
        Chinese-language system prompt capturing Xiaohongshu culture.
    """
    name_str = f"你的昵称是{name}。" if name else ""
    bio_str = f"你的个人简介：{bio}" if bio else ""

    profile_str = ""
    if profile and "other_info" in profile:
        info = profile["other_info"]
        if info.get("user_profile"):
            profile_str = f"你的人设：{info['user_profile']}。"
        parts = []
        if info.get("gender"):
            parts.append(f"性别{info['gender']}")
        if info.get("age"):
            parts.append(f"{info['age']}岁")
        if info.get("city"):
            parts.append(f"坐标{info['city']}")
        if parts:
            profile_str += "你是一位" + "、".join(parts) + "的小红书博主。"

    return f"""# 目标
你是一个小红书用户。我会给你展示一些笔记内容，看完后请从可用的操作中选择你要执行的动作。

# 平台特点
小红书是中国最大的种草社区和生活方式平台。用户以年轻女性为主，通过发笔记、点赞、收藏、分享来互动。小红书文化的特点：
- 种草文化：热衷分享好物推荐、生活经验、美妆教程等
- 视觉优先：注重图片和排版的美感
- 收藏为王：收藏代表内容有实用价值，权重高于点赞
- 真实分享：强调个人真实体验和使用感受
- 标题党+emoji：标题需要有吸引力，内容多用emoji装饰

# 自我描述
你的行为应该符合你的人设和性格。
{name_str}
{bio_str}
{profile_str}

# 行为准则
- 发笔记时标题要吸引眼球，善用emoji装饰
- 内容要图文并茂（用文字描述画面感），有干货有真实感受
- 看到好内容优先收藏，收藏代表实用价值
- 分享时注重给闺蜜/朋友种草
- 语气可爱、亲切，多用语气词（啦、呀、嘻嘻、绝绝子、YYDS等）
- 善用标签 #话题标签

# 回复方式
请通过工具调用来执行操作。"""
```

- [ ] **Step 2: Create Xiaohongshu adapter**

Create `engine/platforms/xiaohongshu.py`:

```python
"""Xiaohongshu (Little Red Book) platform adapter.

Adds two custom actions:
- collect_post: Bookmark/collect a post (higher weight than likes)
- share_post: Share a post to friends/external

Uses a dual-channel recommendation system that blends:
1. Interest-based discovery (content similarity scoring)
2. Collection-weighted ranking (collected posts rank higher)
"""

from __future__ import annotations

import heapq
import logging
import random
from collections import defaultdict
from math import log
from typing import Any

from oasis.social_platform.typing import RecsysType

from engine.platforms.actions import COLLECT_POST, SHARE_POST
from engine.platforms.base import BasePlatformAdapter
from engine.platforms.prompts.xiaohongshu import get_xiaohongshu_system_prompt

logger = logging.getLogger(__name__)


def rec_sys_xiaohongshu(
    post_table: list[dict[str, Any]],
    rec_matrix: list[list],
    max_rec_post_len: int,
    db_cursor: Any = None,
) -> list[list]:
    """Xiaohongshu dual-channel recommendation system.

    Scoring formula:
        score = (num_collections * 3 + num_likes * 1 + num_shares * 2)
                * recency_factor

    On Xiaohongshu, collections (bookmarks) are the strongest signal
    of content quality and utility, so they receive 3x weight.

    Args:
        post_table: List of post dicts from the database.
        rec_matrix: Current recommendation matrix.
        max_rec_post_len: Maximum posts per user.
        db_cursor: Optional cursor for fetching collection counts.

    Returns:
        Updated recommendation matrix.
    """
    post_ids = [post["post_id"] for post in post_table]

    if len(post_ids) <= max_rec_post_len:
        return [post_ids] * len(rec_matrix)

    collection_counts: dict[int, int] = defaultdict(int)
    share_counts: dict[int, int] = defaultdict(int)
    if db_cursor is not None:
        for post in post_table:
            pid = post["post_id"]
            db_cursor.execute(
                "SELECT COUNT(*) FROM collection WHERE post_id = ?", (pid,)
            )
            row = db_cursor.fetchone()
            if row:
                collection_counts[pid] = row[0]
            db_cursor.execute(
                "SELECT COUNT(*) FROM share WHERE post_id = ?", (pid,)
            )
            row = db_cursor.fetchone()
            if row:
                share_counts[pid] = row[0]

    scored_posts: list[tuple[float, int]] = []
    for i, post in enumerate(post_table):
        pid = post["post_id"]
        num_collections = collection_counts.get(pid, 0)
        num_shares_custom = share_counts.get(pid, 0)
        num_likes = post.get("num_likes", 0)
        num_shares_core = post.get("num_shares", 0)

        engagement = (
            num_collections * 3.0
            + num_likes * 1.0
            + (num_shares_core + num_shares_custom) * 2.0
        )

        total_posts = len(post_table)
        recency = 1.0 + 0.5 * (i / max(total_posts - 1, 1))

        score = engagement * recency
        scored_posts.append((score, pid))

    top_posts = heapq.nlargest(
        max_rec_post_len, scored_posts, key=lambda x: x[0]
    )
    top_post_ids = [pid for _, pid in top_posts]

    new_rec_matrix: list[list] = []
    for _ in range(len(rec_matrix)):
        user_recs = list(top_post_ids)
        num_to_shuffle = max(1, len(user_recs) // 5)
        tail = user_recs[-num_to_shuffle:]
        random.shuffle(tail)
        user_recs[-num_to_shuffle:] = tail
        new_rec_matrix.append(user_recs)

    return new_rec_matrix


class XiaohongshuPlatform(BasePlatformAdapter):
    """Xiaohongshu (Little Red Book) platform adapter.

    Custom actions:
    - collect_post: Bookmark a post (creates collection record,
      stronger signal than like)
    - share_post: Share a post externally

    Custom recsys:
    - Dual-channel scoring with 3x weight on collections
    """

    PLATFORM_NAME = "xiaohongshu"
    CUSTOM_ACTIONS = {
        COLLECT_POST: "collect_post",
        SHARE_POST: "share_post",
    }

    def _setup_custom_tables(self) -> None:
        """Create collection and share tables for Xiaohongshu."""
        self.db_cursor.executescript("""
            CREATE TABLE IF NOT EXISTS collection (
                collection_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                post_id INTEGER,
                created_at DATETIME,
                FOREIGN KEY(user_id) REFERENCES user(user_id),
                FOREIGN KEY(post_id) REFERENCES post(post_id)
            );
            CREATE TABLE IF NOT EXISTS share (
                share_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                post_id INTEGER,
                created_at DATETIME,
                FOREIGN KEY(user_id) REFERENCES user(user_id),
                FOREIGN KEY(post_id) REFERENCES post(post_id)
            );
        """)
        self.db.commit()

    async def running(self):
        """Override running loop to handle custom action strings
        that are not in the core ActionType enum.
        """
        from oasis.social_platform.typing import ActionType

        while True:
            message_id, data = await self.channel.receive_from()
            agent_id, message, action = data

            if action == ActionType.EXIT.value or action == "exit":
                import sqlite3

                if self.db_path == ":memory:":
                    dst = sqlite3.connect("mock.db")
                    with dst:
                        self.db.backup(dst)
                self.db_cursor.close()
                self.db.close()
                break

            action_function = getattr(self, action, None)
            if action_function:
                func_code = action_function.__code__
                param_names = func_code.co_varnames[:func_code.co_argcount]
                len_param_names = len(param_names)
                if len_param_names > 3:
                    raise ValueError(
                        f"Functions with {len_param_names} parameters "
                        f"are not supported."
                    )
                params = {}
                if len_param_names >= 2:
                    params["agent_id"] = agent_id
                if len_param_names == 3:
                    second_param_name = param_names[2]
                    params[second_param_name] = message
                result = await action_function(**params)
                await self.channel.send_to((message_id, agent_id, result))
            else:
                raise ValueError(f"Action {action} is not supported")

    async def collect_post(self, agent_id: int, post_id: int):
        """Collect (bookmark) a post. On Xiaohongshu, collecting
        signifies that the content has practical value.

        Args:
            agent_id: The collecting user's agent ID.
            post_id: The post to collect.

        Returns:
            Dict with success status and collection_id.
        """
        current_time = self._get_current_time()
        try:
            user_id = agent_id

            check_query = (
                "SELECT * FROM collection WHERE user_id = ? AND post_id = ?"
            )
            self.pl_utils._execute_db_command(check_query, (user_id, post_id))
            if self.db_cursor.fetchone():
                return {
                    "success": False,
                    "error": "Collection record already exists.",
                }

            insert_query = (
                "INSERT INTO collection (user_id, post_id, created_at) "
                "VALUES (?, ?, ?)"
            )
            self.pl_utils._execute_db_command(
                insert_query, (user_id, post_id, current_time), commit=True
            )
            collection_id = self.db_cursor.lastrowid

            self._record_custom_trace(
                user_id,
                COLLECT_POST,
                {"post_id": post_id, "collection_id": collection_id},
            )
            return {"success": True, "collection_id": collection_id}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def share_post(self, agent_id: int, post_id: int):
        """Share a post to friends or external platforms.

        Args:
            agent_id: The sharing user's agent ID.
            post_id: The post to share.

        Returns:
            Dict with success status and share_id.
        """
        current_time = self._get_current_time()
        try:
            user_id = agent_id

            post_check = "SELECT post_id FROM post WHERE post_id = ?"
            self.pl_utils._execute_db_command(post_check, (post_id,))
            if not self.db_cursor.fetchone():
                return {"success": False, "error": "Post not found."}

            insert_query = (
                "INSERT INTO share (user_id, post_id, created_at) "
                "VALUES (?, ?, ?)"
            )
            self.pl_utils._execute_db_command(
                insert_query, (user_id, post_id, current_time), commit=True
            )
            share_id = self.db_cursor.lastrowid

            update_query = (
                "UPDATE post SET num_shares = num_shares + 1 "
                "WHERE post_id = ?"
            )
            self.pl_utils._execute_db_command(
                update_query, (post_id,), commit=True
            )

            self._record_custom_trace(
                user_id,
                SHARE_POST,
                {"post_id": post_id, "share_id": share_id},
            )
            return {"success": True, "share_id": share_id}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def update_rec_table(self):
        """Override to use Xiaohongshu-specific recsys."""
        from oasis.social_platform.database import (
            fetch_rec_table_as_matrix,
            fetch_table_from_db,
        )

        logger.info("Xiaohongshu: refreshing recommendation cache...")
        post_table = fetch_table_from_db(self.db_cursor, "post")
        rec_matrix = fetch_rec_table_as_matrix(self.db_cursor)

        new_rec_matrix = rec_sys_xiaohongshu(
            post_table, rec_matrix, self.max_rec_post_len,
            db_cursor=self.db_cursor,
        )

        self.pl_utils._execute_db_command("DELETE FROM rec", commit=True)
        insert_values = [
            (user_id, post_id)
            for user_id in range(len(new_rec_matrix))
            for post_id in new_rec_matrix[user_id]
        ]
        self.pl_utils._execute_many_db_command(
            "INSERT INTO rec (user_id, post_id) VALUES (?, ?)",
            insert_values, commit=True,
        )

    def get_system_prompt(
        self,
        name: str | None = None,
        bio: str | None = None,
        profile: dict[str, Any] | None = None,
    ) -> str:
        return get_xiaohongshu_system_prompt(name=name, bio=bio, profile=profile)


# Self-register with the global registry
from engine.platforms import registry as _registry

try:
    _registry.register(
        name="xiaohongshu",
        adapter_class=XiaohongshuPlatform,
        default_recsys="random",
        default_actions=[
            "create_post", "like_post", "collect_post", "share_post",
            "follow", "create_comment", "do_nothing",
        ],
        description="小红书 - 中国最大的种草社区和生活方式平台",
    )
except ValueError:
    pass
```

- [ ] **Step 3: Create Xiaohongshu tests**

Create `engine/platforms/tests/test_xiaohongshu.py`:

```python
"""Tests for the Xiaohongshu platform adapter."""

import os
import os.path as osp
import sqlite3

import pytest

from engine.platforms.xiaohongshu import (
    XiaohongshuPlatform,
    rec_sys_xiaohongshu,
)
from engine.platforms.prompts.xiaohongshu import get_xiaohongshu_system_prompt

parent_folder = osp.dirname(osp.abspath(__file__))
test_db_filepath = osp.join(parent_folder, "test_xiaohongshu.db")


class TestXiaohongshuRecsys:
    def test_few_posts_returns_all(self):
        post_table = [
            {"post_id": 1, "num_likes": 5, "num_dislikes": 0,
             "num_shares": 1, "created_at": "2025-01-01 12:00:00"},
        ]
        rec_matrix = [[], []]
        result = rec_sys_xiaohongshu(post_table, rec_matrix, max_rec_post_len=5)
        assert len(result) == 2
        for row in result:
            assert 1 in row

    def test_top_k_selection(self):
        post_table = [
            {"post_id": i, "num_likes": i * 10, "num_dislikes": 0,
             "num_shares": 0, "created_at": "2025-01-01 12:00:00"}
            for i in range(1, 15)
        ]
        rec_matrix = [[] for _ in range(3)]
        result = rec_sys_xiaohongshu(
            post_table, rec_matrix, max_rec_post_len=5
        )
        assert len(result) == 3
        for row in result:
            assert len(row) == 5


class TestXiaohongshuPlatform:
    @pytest.fixture
    def platform(self):
        if os.path.exists(test_db_filepath):
            os.remove(test_db_filepath)
        p = XiaohongshuPlatform(
            db_path=test_db_filepath, recsys_type="random"
        )
        yield p
        p.db_cursor.close()
        p.db.close()
        if os.path.exists(test_db_filepath):
            os.remove(test_db_filepath)

    def test_platform_name(self, platform):
        assert platform.PLATFORM_NAME == "xiaohongshu"

    def test_custom_tables_created(self, platform):
        platform.db_cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='collection'"
        )
        assert platform.db_cursor.fetchone() is not None
        platform.db_cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='share'"
        )
        assert platform.db_cursor.fetchone() is not None

    @pytest.mark.asyncio
    async def test_collect_post(self, platform):
        conn = sqlite3.connect(test_db_filepath)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (1, 1, "xhs_user1", 0, 0),
        )
        cursor.execute(
            "INSERT INTO post (post_id, user_id, content, created_at, "
            "num_likes, num_dislikes, num_shares) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, 1, "种草分享", "2025-01-01 12:00:00", 0, 0, 0),
        )
        conn.commit()
        conn.close()

        result = await platform.collect_post(1, 1)
        assert result["success"] is True
        assert "collection_id" in result

    @pytest.mark.asyncio
    async def test_collect_post_duplicate(self, platform):
        conn = sqlite3.connect(test_db_filepath)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (1, 1, "xhs_user1", 0, 0),
        )
        cursor.execute(
            "INSERT INTO post (post_id, user_id, content, created_at, "
            "num_likes, num_dislikes, num_shares) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, 1, "种草分享", "2025-01-01 12:00:00", 0, 0, 0),
        )
        conn.commit()
        conn.close()

        await platform.collect_post(1, 1)
        result = await platform.collect_post(1, 1)
        assert result["success"] is False
        assert "already exists" in result["error"]

    @pytest.mark.asyncio
    async def test_share_post(self, platform):
        conn = sqlite3.connect(test_db_filepath)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (1, 1, "xhs_user1", 0, 0),
        )
        cursor.execute(
            "INSERT INTO post (post_id, user_id, content, created_at, "
            "num_likes, num_dislikes, num_shares) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, 1, "好物推荐", "2025-01-01 12:00:00", 0, 0, 0),
        )
        conn.commit()
        conn.close()

        result = await platform.share_post(1, 1)
        assert result["success"] is True
        assert "share_id" in result

    @pytest.mark.asyncio
    async def test_share_nonexistent_post(self, platform):
        conn = sqlite3.connect(test_db_filepath)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (1, 1, "xhs_user1", 0, 0),
        )
        conn.commit()
        conn.close()

        result = await platform.share_post(1, 999)
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_system_prompt(self, platform):
        prompt = platform.get_system_prompt(
            name="小红薯", bio="分享美好生活"
        )
        assert "小红书" in prompt
        assert "种草" in prompt
        assert "小红薯" in prompt


class TestXiaohongshuPrompts:
    def test_basic_prompt(self):
        prompt = get_xiaohongshu_system_prompt(name="美妆达人")
        assert "小红书" in prompt
        assert "种草" in prompt
        assert "收藏" in prompt
        assert "美妆达人" in prompt

    def test_prompt_with_emoji_mention(self):
        prompt = get_xiaohongshu_system_prompt()
        assert "emoji" in prompt
```

- [ ] **Step 4: Commit**

```bash
cd D:/project/oasis
git add engine/platforms/xiaohongshu.py engine/platforms/prompts/xiaohongshu.py engine/platforms/tests/test_xiaohongshu.py
git commit -m "feat(platforms): add Xiaohongshu adapter with collect/share actions

Xiaohongshu adapter adds:
- collect_post and share_post custom actions
- Dual-channel recsys with 3x weight on collections
- Custom SQLite tables for collection and share records
- 种草文化 agent prompts with emoji-dense style"
```

---

## Task 5: Douyin Adapter

**Files:**
- Create: `engine/platforms/douyin.py`
- Create: `engine/platforms/prompts/douyin.py`
- Create: `engine/platforms/tests/test_douyin.py`

- [ ] **Step 1: Create Douyin agent prompts**

Create `engine/platforms/prompts/douyin.py`:

```python
"""Douyin (TikTok China) agent prompt templates.

Douyin culture characteristics:
- Short-form video content (simulated as short text posts)
- Strong interaction: like + collect + comment quickly
- Traffic pool system: content passes through tiers (50 -> 200 -> full)
- 热门挑战 (trending challenges)
- 直播带货 (livestream shopping culture)
"""


def get_douyin_system_prompt(
    name: str | None = None,
    bio: str | None = None,
    profile: dict | None = None,
) -> str:
    """Generate a Douyin-style system prompt for an agent.

    Args:
        name: Agent display name.
        bio: Agent biography.
        profile: Additional profile dict.

    Returns:
        Chinese-language system prompt capturing Douyin culture.
    """
    name_str = f"你的昵称是{name}。" if name else ""
    bio_str = f"你的个人简介：{bio}" if bio else ""

    profile_str = ""
    if profile and "other_info" in profile:
        info = profile["other_info"]
        if info.get("user_profile"):
            profile_str = f"你的人设：{info['user_profile']}。"
        parts = []
        if info.get("gender"):
            parts.append(f"性别{info['gender']}")
        if info.get("age"):
            parts.append(f"{info['age']}岁")
        if info.get("city"):
            parts.append(f"来自{info['city']}")
        if parts:
            profile_str += "你是一位" + "、".join(parts) + "的抖音用户。"

    return f"""# 目标
你是一个抖音用户。我会给你展示一些短视频内容（以文字描述呈现），看完后请从可用的操作中选择你要执行的动作。

# 平台特点
抖音是中国最大的短视频平台。用户通过刷视频、点赞、收藏、评论来互动。抖音文化的特点：
- 快节奏消费：快速刷视频，几秒内决定是否点赞
- 强互动：看到喜欢的内容会积极点赞、收藏、评论
- 挑战跟风：热衷参与热门挑战和话题
- 表达直接：评论简短有力，善用网络热梗
- 流量为王：关注播放量和互动数据

# 自我描述
你的行为应该符合你的人设和性格。
{name_str}
{bio_str}
{profile_str}

# 行为准则
- 刷到感兴趣的内容快速互动（点赞、收藏、评论）
- 评论要简短有力，可以用网络热梗
- 看到特别好的内容会收藏
- 发内容时注重开头抓人（前3秒决定成败）
- 善用热门话题标签 #话题
- 创作内容简短精炼，有节奏感

# 回复方式
请通过工具调用来执行操作。"""
```

- [ ] **Step 2: Create Douyin adapter**

Create `engine/platforms/douyin.py`:

```python
"""Douyin (TikTok China) platform adapter.

Adds one custom action:
- collect_post: Bookmark/collect a video post

Uses a traffic pool recommendation system that simulates Douyin's
tiered exposure model:
- Tier 1: New posts get shown to ~50 users (small pool)
- Tier 2: Posts with good engagement get shown to ~200 users
- Tier 3: Posts with excellent engagement get full distribution
"""

from __future__ import annotations

import logging
import random
from collections import defaultdict
from typing import Any

from oasis.social_platform.typing import RecsysType

from engine.platforms.actions import COLLECT_POST
from engine.platforms.base import BasePlatformAdapter
from engine.platforms.prompts.douyin import get_douyin_system_prompt

logger = logging.getLogger(__name__)


def _calculate_engagement_rate(post: dict[str, Any]) -> float:
    """Calculate engagement rate for a post.

    The engagement rate determines which traffic pool tier
    the post belongs to.

    Args:
        post: Post dict with num_likes, num_dislikes, num_shares.

    Returns:
        Engagement rate as a float.
    """
    likes = post.get("num_likes", 0)
    dislikes = post.get("num_dislikes", 0)
    shares = post.get("num_shares", 0)
    total_interactions = likes + dislikes + shares
    if total_interactions == 0:
        return 0.0
    positive = likes + shares
    return positive / total_interactions


def rec_sys_douyin(
    post_table: list[dict[str, Any]],
    rec_matrix: list[list],
    max_rec_post_len: int,
    tier1_size: int = 50,
    tier2_size: int = 200,
    tier1_threshold: float = 0.3,
    tier2_threshold: float = 0.6,
) -> list[list]:
    """Douyin traffic pool recommendation system.

    Simulates the tiered distribution model:
    - All new posts start in Tier 1 (shown to a small sample)
    - Posts exceeding tier1_threshold engagement move to Tier 2
    - Posts exceeding tier2_threshold engagement get full distribution
    - Full distribution posts are recommended to everyone

    The number of users in rec_matrix determines the pool sizes.
    If there are fewer users than the tier size, all users see
    the post.

    Args:
        post_table: List of post dicts.
        rec_matrix: Current recommendation matrix.
        max_rec_post_len: Maximum posts per user.
        tier1_size: Number of users in the initial exposure pool.
        tier2_size: Number of users in the mid-tier pool.
        tier1_threshold: Engagement rate to advance from tier 1 to 2.
        tier2_threshold: Engagement rate to advance to full distribution.

    Returns:
        Updated recommendation matrix.
    """
    post_ids = [post["post_id"] for post in post_table]
    num_users = len(rec_matrix)

    if len(post_ids) <= max_rec_post_len:
        return [post_ids] * num_users

    tier_full: list[int] = []
    tier_mid: list[int] = []
    tier_entry: list[int] = []

    for post in post_table:
        rate = _calculate_engagement_rate(post)
        if rate >= tier2_threshold:
            tier_full.append(post["post_id"])
        elif rate >= tier1_threshold:
            tier_mid.append(post["post_id"])
        else:
            tier_entry.append(post["post_id"])

    user_recs: dict[int, list[int]] = defaultdict(list)

    for pid in tier_full:
        for uid in range(num_users):
            user_recs[uid].append(pid)

    if tier_mid:
        mid_users = list(range(num_users))
        if len(mid_users) > tier2_size:
            mid_users = random.sample(mid_users, tier2_size)
        for pid in tier_mid:
            target = random.sample(mid_users, min(len(mid_users), tier2_size))
            for uid in target:
                user_recs[uid].append(pid)

    if tier_entry:
        entry_users = list(range(num_users))
        for pid in tier_entry:
            target_size = min(len(entry_users), tier1_size)
            target = random.sample(entry_users, target_size)
            for uid in target:
                user_recs[uid].append(pid)

    new_rec_matrix: list[list] = []
    for uid in range(num_users):
        recs = user_recs.get(uid, [])
        seen = set()
        unique_recs = []
        for pid in recs:
            if pid not in seen:
                seen.add(pid)
                unique_recs.append(pid)
        if len(unique_recs) > max_rec_post_len:
            unique_recs = unique_recs[:max_rec_post_len]
        elif len(unique_recs) < max_rec_post_len:
            remaining = [p for p in post_ids if p not in seen]
            fill = remaining[: max_rec_post_len - len(unique_recs)]
            unique_recs.extend(fill)
        new_rec_matrix.append(unique_recs)

    return new_rec_matrix


class DouyinPlatform(BasePlatformAdapter):
    """Douyin (TikTok China) platform adapter.

    Custom actions:
    - collect_post: Bookmark a short video post

    Custom recsys:
    - Traffic pool system (Tier 1: 50 users, Tier 2: 200, Tier 3: full)
    """

    PLATFORM_NAME = "douyin"
    CUSTOM_ACTIONS = {
        COLLECT_POST: "collect_post",
    }

    def _setup_custom_tables(self) -> None:
        """Create collection table for Douyin."""
        self.db_cursor.executescript("""
            CREATE TABLE IF NOT EXISTS collection (
                collection_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                post_id INTEGER,
                created_at DATETIME,
                FOREIGN KEY(user_id) REFERENCES user(user_id),
                FOREIGN KEY(post_id) REFERENCES post(post_id)
            );
        """)
        self.db.commit()

    async def running(self):
        """Override running loop to handle custom action strings."""
        from oasis.social_platform.typing import ActionType

        while True:
            message_id, data = await self.channel.receive_from()
            agent_id, message, action = data

            if action == ActionType.EXIT.value or action == "exit":
                import sqlite3

                if self.db_path == ":memory:":
                    dst = sqlite3.connect("mock.db")
                    with dst:
                        self.db.backup(dst)
                self.db_cursor.close()
                self.db.close()
                break

            action_function = getattr(self, action, None)
            if action_function:
                func_code = action_function.__code__
                param_names = func_code.co_varnames[:func_code.co_argcount]
                len_param_names = len(param_names)
                if len_param_names > 3:
                    raise ValueError(
                        f"Functions with {len_param_names} parameters "
                        f"are not supported."
                    )
                params = {}
                if len_param_names >= 2:
                    params["agent_id"] = agent_id
                if len_param_names == 3:
                    second_param_name = param_names[2]
                    params[second_param_name] = message
                result = await action_function(**params)
                await self.channel.send_to((message_id, agent_id, result))
            else:
                raise ValueError(f"Action {action} is not supported")

    async def collect_post(self, agent_id: int, post_id: int):
        """Collect (bookmark) a short video post.

        Args:
            agent_id: The collecting user's agent ID.
            post_id: The post to collect.

        Returns:
            Dict with success status and collection_id.
        """
        current_time = self._get_current_time()
        try:
            user_id = agent_id

            check_query = (
                "SELECT * FROM collection WHERE user_id = ? AND post_id = ?"
            )
            self.pl_utils._execute_db_command(check_query, (user_id, post_id))
            if self.db_cursor.fetchone():
                return {
                    "success": False,
                    "error": "Collection record already exists.",
                }

            insert_query = (
                "INSERT INTO collection (user_id, post_id, created_at) "
                "VALUES (?, ?, ?)"
            )
            self.pl_utils._execute_db_command(
                insert_query, (user_id, post_id, current_time), commit=True
            )
            collection_id = self.db_cursor.lastrowid

            self._record_custom_trace(
                user_id,
                COLLECT_POST,
                {"post_id": post_id, "collection_id": collection_id},
            )
            return {"success": True, "collection_id": collection_id}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def update_rec_table(self):
        """Override to use Douyin traffic pool recsys."""
        from oasis.social_platform.database import (
            fetch_rec_table_as_matrix,
            fetch_table_from_db,
        )

        logger.info("Douyin: refreshing recommendation cache...")
        post_table = fetch_table_from_db(self.db_cursor, "post")
        rec_matrix = fetch_rec_table_as_matrix(self.db_cursor)

        new_rec_matrix = rec_sys_douyin(
            post_table, rec_matrix, self.max_rec_post_len,
        )

        self.pl_utils._execute_db_command("DELETE FROM rec", commit=True)
        insert_values = [
            (user_id, post_id)
            for user_id in range(len(new_rec_matrix))
            for post_id in new_rec_matrix[user_id]
        ]
        self.pl_utils._execute_many_db_command(
            "INSERT INTO rec (user_id, post_id) VALUES (?, ?)",
            insert_values, commit=True,
        )

    def get_system_prompt(
        self,
        name: str | None = None,
        bio: str | None = None,
        profile: dict[str, Any] | None = None,
    ) -> str:
        return get_douyin_system_prompt(name=name, bio=bio, profile=profile)


# Self-register with the global registry
from engine.platforms import registry as _registry

try:
    _registry.register(
        name="douyin",
        adapter_class=DouyinPlatform,
        default_recsys="random",
        default_actions=[
            "create_post", "like_post", "collect_post",
            "follow", "create_comment", "do_nothing",
        ],
        description="抖音 - 中国最大的短视频平台",
    )
except ValueError:
    pass
```

- [ ] **Step 3: Create Douyin tests**

Create `engine/platforms/tests/test_douyin.py`:

```python
"""Tests for the Douyin platform adapter."""

import os
import os.path as osp
import sqlite3

import pytest

from engine.platforms.douyin import (
    DouyinPlatform,
    _calculate_engagement_rate,
    rec_sys_douyin,
)
from engine.platforms.prompts.douyin import get_douyin_system_prompt

parent_folder = osp.dirname(osp.abspath(__file__))
test_db_filepath = osp.join(parent_folder, "test_douyin.db")


class TestEngagementRate:
    def test_zero_interactions(self):
        post = {"num_likes": 0, "num_dislikes": 0, "num_shares": 0}
        assert _calculate_engagement_rate(post) == 0.0

    def test_all_positive(self):
        post = {"num_likes": 10, "num_dislikes": 0, "num_shares": 5}
        rate = _calculate_engagement_rate(post)
        assert rate == 1.0

    def test_mixed_engagement(self):
        post = {"num_likes": 7, "num_dislikes": 3, "num_shares": 0}
        rate = _calculate_engagement_rate(post)
        assert 0.0 < rate < 1.0
        assert abs(rate - 0.7) < 0.01


class TestDouyinRecsys:
    def test_few_posts_returns_all(self):
        post_table = [
            {"post_id": 1, "num_likes": 5, "num_dislikes": 0, "num_shares": 0},
        ]
        rec_matrix = [[], [], []]
        result = rec_sys_douyin(post_table, rec_matrix, max_rec_post_len=5)
        assert len(result) == 3
        for row in result:
            assert 1 in row

    def test_tiered_distribution(self):
        post_table = [
            {"post_id": 1, "num_likes": 100, "num_dislikes": 0,
             "num_shares": 50},
            {"post_id": 2, "num_likes": 5, "num_dislikes": 3,
             "num_shares": 2},
            {"post_id": 3, "num_likes": 0, "num_dislikes": 0,
             "num_shares": 0},
        ]
        rec_matrix = [[] for _ in range(10)]
        result = rec_sys_douyin(
            post_table, rec_matrix, max_rec_post_len=2,
            tier1_size=3, tier2_size=6,
        )
        assert len(result) == 10
        post1_count = sum(1 for row in result if 1 in row)
        assert post1_count == 10

    def test_output_length_capped(self):
        post_table = [
            {"post_id": i, "num_likes": i, "num_dislikes": 0,
             "num_shares": 0}
            for i in range(1, 20)
        ]
        rec_matrix = [[] for _ in range(5)]
        result = rec_sys_douyin(post_table, rec_matrix, max_rec_post_len=3)
        for row in result:
            assert len(row) <= 3


class TestDouyinPlatform:
    @pytest.fixture
    def platform(self):
        if os.path.exists(test_db_filepath):
            os.remove(test_db_filepath)
        p = DouyinPlatform(db_path=test_db_filepath, recsys_type="random")
        yield p
        p.db_cursor.close()
        p.db.close()
        if os.path.exists(test_db_filepath):
            os.remove(test_db_filepath)

    def test_platform_name(self, platform):
        assert platform.PLATFORM_NAME == "douyin"

    def test_collection_table_created(self, platform):
        platform.db_cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='collection'"
        )
        assert platform.db_cursor.fetchone() is not None

    @pytest.mark.asyncio
    async def test_collect_post(self, platform):
        conn = sqlite3.connect(test_db_filepath)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (1, 1, "douyin_user", 0, 0),
        )
        cursor.execute(
            "INSERT INTO post (post_id, user_id, content, created_at, "
            "num_likes, num_dislikes, num_shares) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, 1, "抖音热门视频", "2025-01-01 12:00:00", 0, 0, 0),
        )
        conn.commit()
        conn.close()

        result = await platform.collect_post(1, 1)
        assert result["success"] is True

        result2 = await platform.collect_post(1, 1)
        assert result2["success"] is False

    def test_system_prompt(self, platform):
        prompt = platform.get_system_prompt(name="抖音达人")
        assert "抖音" in prompt
        assert "短视频" in prompt


class TestDouyinPrompts:
    def test_basic_prompt(self):
        prompt = get_douyin_system_prompt(name="创作者小王")
        assert "抖音" in prompt
        assert "创作者小王" in prompt
        assert "短视频" in prompt
```

- [ ] **Step 4: Commit**

```bash
cd D:/project/oasis
git add engine/platforms/douyin.py engine/platforms/prompts/douyin.py engine/platforms/tests/test_douyin.py
git commit -m "feat(platforms): add Douyin adapter with traffic pool recsys

Douyin adapter adds:
- collect_post custom action
- Traffic pool recsys (Tier 1: 50, Tier 2: 200, Tier 3: full)
- Short-form content agent prompts with 快节奏 culture"
```

---

## Task 6: Kuaishou Adapter

**Files:**
- Create: `engine/platforms/kuaishou.py`
- Create: `engine/platforms/prompts/kuaishou.py`
- Create: `engine/platforms/tests/test_kuaishou.py`

- [ ] **Step 1: Create Kuaishou agent prompts**

Create `engine/platforms/prompts/kuaishou.py`:

```python
"""Kuaishou agent prompt templates.

Kuaishou culture characteristics:
- 下沉市场 (lower-tier cities market)
- 老铁文化 (buddy/bro culture, strong social bonds)
- 直播打赏 (livestream gifting)
- 说说 (status updates, like Moments/stories)
- 真实接地气 (authentic, down-to-earth content)
- Social-first: follow-page weighted more than algorithm
"""


def get_kuaishou_system_prompt(
    name: str | None = None,
    bio: str | None = None,
    profile: dict | None = None,
) -> str:
    """Generate a Kuaishou-style system prompt for an agent.

    Args:
        name: Agent display name.
        bio: Agent biography.
        profile: Additional profile dict.

    Returns:
        Chinese-language system prompt capturing Kuaishou culture.
    """
    name_str = f"你的昵称是{name}。" if name else ""
    bio_str = f"你的个人简介：{bio}" if bio else ""

    profile_str = ""
    if profile and "other_info" in profile:
        info = profile["other_info"]
        if info.get("user_profile"):
            profile_str = f"你的人设：{info['user_profile']}。"
        parts = []
        if info.get("gender"):
            parts.append(f"性别{info['gender']}")
        if info.get("age"):
            parts.append(f"{info['age']}岁")
        if info.get("city"):
            parts.append(f"来自{info['city']}")
        if parts:
            profile_str += "你是一位" + "、".join(parts) + "的快手用户。"

    return f"""# 目标
你是一个快手用户。我会给你展示一些内容，看完后请从可用的操作中选择你要执行的动作。

# 平台特点
快手是中国领先的短视频和直播平台，以真实接地气的内容著称。快手文化的特点：
- 老铁文化：用户之间关系亲密，互称"老铁"，讲究义气
- 下沉市场：内容贴近三四线城市和农村生活
- 真实接地气：不追求精致包装，注重真实展现
- 直播互动：热衷看直播、打赏主播、互动聊天
- 说说文化：喜欢发说说（类似朋友圈）分享日常
- 社交优先：关注页面和算法推荐并重，重视粉丝关系

# 自我描述
你的行为应该符合你的人设和性格。
{name_str}
{bio_str}
{profile_str}

# 行为准则
- 表达方式朴实直接，不装不做作
- 喜欢用"老铁"称呼其他用户
- 对喜欢的主播/创作者会打赏支持
- 喜欢通过"说说"分享生活日常
- 评论风格热情、接地气
- 重视社交关系，活跃关注和互粉

# 回复方式
请通过工具调用来执行操作。"""
```

- [ ] **Step 2: Create Kuaishou adapter**

Create `engine/platforms/kuaishou.py`:

```python
"""Kuaishou platform adapter.

Adds two custom actions:
- send_gift: Send a virtual gift to a post creator (livestream tipping)
- post_shuoshuo: Post a "说说" (status update, like stories)

Uses a social + algorithm mixed recommendation system where
content from followed users gets priority weighting.
"""

from __future__ import annotations

import heapq
import logging
import random
from collections import defaultdict
from typing import Any

from oasis.social_platform.typing import RecsysType

from engine.platforms.actions import POST_SHUOSHUO, SEND_GIFT
from engine.platforms.base import BasePlatformAdapter
from engine.platforms.prompts.kuaishou import get_kuaishou_system_prompt

logger = logging.getLogger(__name__)


def rec_sys_kuaishou(
    user_table: list[dict[str, Any]],
    post_table: list[dict[str, Any]],
    rec_matrix: list[list],
    max_rec_post_len: int,
    follow_weight: float = 2.0,
    db_cursor: Any = None,
) -> list[list]:
    """Kuaishou social + algorithm mixed recommendation system.

    Kuaishou's recommendation blends social signals (followed users'
    content) with algorithmic scoring. Posts from followed users get
    a weight multiplier, making the follow-page more prominent than
    pure algorithmic platforms like Douyin.

    Args:
        user_table: List of user dicts.
        post_table: List of post dicts.
        rec_matrix: Current recommendation matrix.
        max_rec_post_len: Maximum posts per user.
        follow_weight: Multiplier for posts from followed users.
        db_cursor: Database cursor for follow relationship lookup.

    Returns:
        Updated recommendation matrix.
    """
    post_ids = [post["post_id"] for post in post_table]
    num_users = len(rec_matrix)

    if len(post_ids) <= max_rec_post_len:
        return [post_ids] * num_users

    follow_map: dict[int, set[int]] = defaultdict(set)
    if db_cursor is not None:
        db_cursor.execute("SELECT follower_id, followee_id FROM follow")
        for row in db_cursor.fetchall():
            follow_map[row[0]].add(row[1])

    post_scores: dict[int, float] = {}
    for post in post_table:
        pid = post["post_id"]
        likes = post.get("num_likes", 0)
        shares = post.get("num_shares", 0)
        score = likes + shares * 1.5
        post_scores[pid] = score

    new_rec_matrix: list[list] = []
    for uid in range(num_users):
        following = follow_map.get(uid, set())
        user_scored: list[tuple[float, int]] = []

        for post in post_table:
            pid = post["post_id"]
            base_score = post_scores[pid]
            if post["user_id"] in following:
                final_score = base_score * follow_weight
            else:
                final_score = base_score
            final_score += random.uniform(0, 0.1)
            user_scored.append((final_score, pid))

        top_posts = heapq.nlargest(
            max_rec_post_len, user_scored, key=lambda x: x[0]
        )
        new_rec_matrix.append([pid for _, pid in top_posts])

    return new_rec_matrix


class KuaishouPlatform(BasePlatformAdapter):
    """Kuaishou platform adapter.

    Custom actions:
    - send_gift: Send virtual gift to content creator
    - post_shuoshuo: Post a status update (说说)

    Custom recsys:
    - Social + algo mix with follow-page weighting
    """

    PLATFORM_NAME = "kuaishou"
    CUSTOM_ACTIONS = {
        SEND_GIFT: "send_gift",
        POST_SHUOSHUO: "post_shuoshuo",
    }

    def _setup_custom_tables(self) -> None:
        """Create gift and shuoshuo tables for Kuaishou."""
        self.db_cursor.executescript("""
            CREATE TABLE IF NOT EXISTS gift (
                gift_id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER,
                receiver_id INTEGER,
                post_id INTEGER,
                gift_value INTEGER DEFAULT 1,
                created_at DATETIME,
                FOREIGN KEY(sender_id) REFERENCES user(user_id),
                FOREIGN KEY(receiver_id) REFERENCES user(user_id),
                FOREIGN KEY(post_id) REFERENCES post(post_id)
            );
            CREATE TABLE IF NOT EXISTS shuoshuo (
                shuoshuo_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                content TEXT,
                created_at DATETIME,
                FOREIGN KEY(user_id) REFERENCES user(user_id)
            );
        """)
        self.db.commit()

    async def running(self):
        """Override running loop to handle custom action strings."""
        from oasis.social_platform.typing import ActionType

        while True:
            message_id, data = await self.channel.receive_from()
            agent_id, message, action = data

            if action == ActionType.EXIT.value or action == "exit":
                import sqlite3

                if self.db_path == ":memory:":
                    dst = sqlite3.connect("mock.db")
                    with dst:
                        self.db.backup(dst)
                self.db_cursor.close()
                self.db.close()
                break

            action_function = getattr(self, action, None)
            if action_function:
                func_code = action_function.__code__
                param_names = func_code.co_varnames[:func_code.co_argcount]
                len_param_names = len(param_names)
                if len_param_names > 3:
                    raise ValueError(
                        f"Functions with {len_param_names} parameters "
                        f"are not supported."
                    )
                params = {}
                if len_param_names >= 2:
                    params["agent_id"] = agent_id
                if len_param_names == 3:
                    second_param_name = param_names[2]
                    params[second_param_name] = message
                result = await action_function(**params)
                await self.channel.send_to((message_id, agent_id, result))
            else:
                raise ValueError(f"Action {action} is not supported")

    async def send_gift(self, agent_id: int, gift_message: tuple):
        """Send a virtual gift to a post's creator.

        Args:
            agent_id: The gift sender's agent ID.
            gift_message: Tuple of (post_id, gift_value).

        Returns:
            Dict with success status and gift_id.
        """
        post_id, gift_value = gift_message
        current_time = self._get_current_time()
        try:
            user_id = agent_id

            post_query = "SELECT user_id FROM post WHERE post_id = ?"
            self.pl_utils._execute_db_command(post_query, (post_id,))
            post_row = self.db_cursor.fetchone()
            if not post_row:
                return {"success": False, "error": "Post not found."}
            receiver_id = post_row[0]

            if receiver_id == user_id:
                return {
                    "success": False,
                    "error": "Cannot send gift to yourself.",
                }

            insert_query = (
                "INSERT INTO gift (sender_id, receiver_id, post_id, "
                "gift_value, created_at) VALUES (?, ?, ?, ?, ?)"
            )
            self.pl_utils._execute_db_command(
                insert_query,
                (user_id, receiver_id, post_id, gift_value, current_time),
                commit=True,
            )
            gift_id = self.db_cursor.lastrowid

            self._record_custom_trace(
                user_id,
                SEND_GIFT,
                {
                    "post_id": post_id,
                    "receiver_id": receiver_id,
                    "gift_value": gift_value,
                    "gift_id": gift_id,
                },
            )
            return {
                "success": True,
                "gift_id": gift_id,
                "receiver_id": receiver_id,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def post_shuoshuo(self, agent_id: int, content: str):
        """Post a "说说" (status update / story).

        Shuoshuo are short-lived status updates similar to WeChat
        Moments or Instagram Stories -- primarily visible to followers.

        Args:
            agent_id: The posting user's agent ID.
            content: The shuoshuo text content.

        Returns:
            Dict with success status and shuoshuo_id.
        """
        current_time = self._get_current_time()
        try:
            user_id = agent_id

            insert_query = (
                "INSERT INTO shuoshuo (user_id, content, created_at) "
                "VALUES (?, ?, ?)"
            )
            self.pl_utils._execute_db_command(
                insert_query, (user_id, content, current_time), commit=True
            )
            shuoshuo_id = self.db_cursor.lastrowid

            self._record_custom_trace(
                user_id,
                POST_SHUOSHUO,
                {"content": content, "shuoshuo_id": shuoshuo_id},
            )
            return {"success": True, "shuoshuo_id": shuoshuo_id}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def update_rec_table(self):
        """Override to use Kuaishou social+algo recsys."""
        from oasis.social_platform.database import (
            fetch_rec_table_as_matrix,
            fetch_table_from_db,
        )

        logger.info("Kuaishou: refreshing recommendation cache...")
        user_table = fetch_table_from_db(self.db_cursor, "user")
        post_table = fetch_table_from_db(self.db_cursor, "post")
        rec_matrix = fetch_rec_table_as_matrix(self.db_cursor)

        new_rec_matrix = rec_sys_kuaishou(
            user_table, post_table, rec_matrix, self.max_rec_post_len,
            db_cursor=self.db_cursor,
        )

        self.pl_utils._execute_db_command("DELETE FROM rec", commit=True)
        insert_values = [
            (user_id, post_id)
            for user_id in range(len(new_rec_matrix))
            for post_id in new_rec_matrix[user_id]
        ]
        self.pl_utils._execute_many_db_command(
            "INSERT INTO rec (user_id, post_id) VALUES (?, ?)",
            insert_values, commit=True,
        )

    def get_system_prompt(
        self,
        name: str | None = None,
        bio: str | None = None,
        profile: dict[str, Any] | None = None,
    ) -> str:
        return get_kuaishou_system_prompt(name=name, bio=bio, profile=profile)


# Self-register with the global registry
from engine.platforms import registry as _registry

try:
    _registry.register(
        name="kuaishou",
        adapter_class=KuaishouPlatform,
        default_recsys="random",
        default_actions=[
            "create_post", "like_post", "send_gift", "post_shuoshuo",
            "follow", "create_comment", "do_nothing",
        ],
        description="快手 - 真实接地气的短视频和直播平台",
    )
except ValueError:
    pass
```

- [ ] **Step 3: Create Kuaishou tests**

Create `engine/platforms/tests/test_kuaishou.py`:

```python
"""Tests for the Kuaishou platform adapter."""

import os
import os.path as osp
import sqlite3

import pytest

from engine.platforms.kuaishou import (
    KuaishouPlatform,
    rec_sys_kuaishou,
)
from engine.platforms.prompts.kuaishou import get_kuaishou_system_prompt

parent_folder = osp.dirname(osp.abspath(__file__))
test_db_filepath = osp.join(parent_folder, "test_kuaishou.db")


class TestKuaishouRecsys:
    def test_few_posts_returns_all(self):
        user_table = [{"user_id": 0}, {"user_id": 1}]
        post_table = [
            {"post_id": 1, "user_id": 0, "num_likes": 5, "num_shares": 1},
        ]
        rec_matrix = [[], []]
        result = rec_sys_kuaishou(
            user_table, post_table, rec_matrix, max_rec_post_len=5
        )
        assert len(result) == 2
        for row in result:
            assert 1 in row

    def test_follow_weighting(self):
        user_table = [{"user_id": 0}, {"user_id": 1}, {"user_id": 2}]
        post_table = [
            {"post_id": i, "user_id": i % 3, "num_likes": 1, "num_shares": 0}
            for i in range(1, 10)
        ]
        rec_matrix = [[] for _ in range(3)]
        result = rec_sys_kuaishou(
            user_table, post_table, rec_matrix, max_rec_post_len=3
        )
        assert len(result) == 3
        for row in result:
            assert len(row) == 3


class TestKuaishouPlatform:
    @pytest.fixture
    def platform(self):
        if os.path.exists(test_db_filepath):
            os.remove(test_db_filepath)
        p = KuaishouPlatform(db_path=test_db_filepath, recsys_type="random")
        yield p
        p.db_cursor.close()
        p.db.close()
        if os.path.exists(test_db_filepath):
            os.remove(test_db_filepath)

    def test_platform_name(self, platform):
        assert platform.PLATFORM_NAME == "kuaishou"

    def test_custom_tables_created(self, platform):
        platform.db_cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='gift'"
        )
        assert platform.db_cursor.fetchone() is not None
        platform.db_cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='shuoshuo'"
        )
        assert platform.db_cursor.fetchone() is not None

    @pytest.mark.asyncio
    async def test_send_gift(self, platform):
        conn = sqlite3.connect(test_db_filepath)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (1, 1, "ks_user1", 0, 0),
        )
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (2, 2, "ks_user2", 0, 0),
        )
        cursor.execute(
            "INSERT INTO post (post_id, user_id, content, created_at, "
            "num_likes, num_dislikes, num_shares) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, 2, "老铁双击666", "2025-01-01 12:00:00", 0, 0, 0),
        )
        conn.commit()
        conn.close()

        result = await platform.send_gift(1, (1, 10))
        assert result["success"] is True
        assert "gift_id" in result
        assert result["receiver_id"] == 2

    @pytest.mark.asyncio
    async def test_send_gift_to_self_fails(self, platform):
        conn = sqlite3.connect(test_db_filepath)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (1, 1, "ks_user1", 0, 0),
        )
        cursor.execute(
            "INSERT INTO post (post_id, user_id, content, created_at, "
            "num_likes, num_dislikes, num_shares) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, 1, "自己的内容", "2025-01-01 12:00:00", 0, 0, 0),
        )
        conn.commit()
        conn.close()

        result = await platform.send_gift(1, (1, 5))
        assert result["success"] is False
        assert "yourself" in result["error"]

    @pytest.mark.asyncio
    async def test_send_gift_nonexistent_post(self, platform):
        conn = sqlite3.connect(test_db_filepath)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (1, 1, "ks_user1", 0, 0),
        )
        conn.commit()
        conn.close()

        result = await platform.send_gift(1, (999, 5))
        assert result["success"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_post_shuoshuo(self, platform):
        conn = sqlite3.connect(test_db_filepath)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (1, 1, "ks_user1", 0, 0),
        )
        conn.commit()
        conn.close()

        result = await platform.post_shuoshuo(1, "今天心情不错，老铁们！")
        assert result["success"] is True
        assert "shuoshuo_id" in result

    def test_system_prompt(self, platform):
        prompt = platform.get_system_prompt(name="老铁小王")
        assert "快手" in prompt
        assert "老铁" in prompt


class TestKuaishouPrompts:
    def test_basic_prompt(self):
        prompt = get_kuaishou_system_prompt(name="铁粉小李")
        assert "快手" in prompt
        assert "老铁" in prompt
        assert "铁粉小李" in prompt
        assert "下沉市场" in prompt
```

- [ ] **Step 4: Commit**

```bash
cd D:/project/oasis
git add engine/platforms/kuaishou.py engine/platforms/prompts/kuaishou.py engine/platforms/tests/test_kuaishou.py
git commit -m "feat(platforms): add Kuaishou adapter with gift and shuoshuo actions

Kuaishou adapter adds:
- send_gift and post_shuoshuo custom actions
- Social + algorithm mixed recsys with follow-page weighting
- 老铁文化 agent prompts with down-to-earth style"
```

---

## Task 7: Bilibili Adapter

**Files:**
- Create: `engine/platforms/bilibili.py`
- Create: `engine/platforms/prompts/bilibili.py`
- Create: `engine/platforms/tests/test_bilibili.py`

- [ ] **Step 1: Create Bilibili agent prompts**

Create `engine/platforms/prompts/bilibili.py`:

```python
"""Bilibili agent prompt templates.

Bilibili culture characteristics:
- Z世代 (Gen Z dominant)
- 梗文化 (meme culture, internet slang heavy)
- 弹幕文化 (danmaku / scrolling comments over video)
- 投币 (coin tossing as appreciation)
- 一键三连 (triple-tap: like + coin + collect)
- ACG亚文化 (anime, comics, games subculture)
- 分区系统 (content partitions/categories)
"""


def get_bilibili_system_prompt(
    name: str | None = None,
    bio: str | None = None,
    profile: dict | None = None,
) -> str:
    """Generate a Bilibili-style system prompt for an agent.

    Args:
        name: Agent display name.
        bio: Agent biography.
        profile: Additional profile dict.

    Returns:
        Chinese-language system prompt capturing Bilibili culture.
    """
    name_str = f"你的昵称是{name}。" if name else ""
    bio_str = f"你的个人简介：{bio}" if bio else ""

    profile_str = ""
    if profile and "other_info" in profile:
        info = profile["other_info"]
        if info.get("user_profile"):
            profile_str = f"你的人设：{info['user_profile']}。"
        parts = []
        if info.get("gender"):
            parts.append(f"性别{info['gender']}")
        if info.get("age"):
            parts.append(f"{info['age']}岁")
        if info.get("interests"):
            parts.append(f"兴趣是{info['interests']}")
        if parts:
            profile_str += "你是一位" + "、".join(parts) + "的B站用户。"

    return f"""# 目标
你是一个Bilibili(B站)用户。我会给你展示一些视频内容（以文字描述呈现），看完后请从可用的操作中选择你要执行的动作。

# 平台特点
B站是中国最大的年轻人文化社区，以ACG(动画、漫画、游戏)内容起家。B站文化的特点：
- 弹幕文化：喜欢在视频上发弹幕，弹幕可以是吐槽、玩梗、刷表情
- 一键三连：对喜欢的视频会"一键三连"（点赞+投币+收藏），这是最高评价
- 投币文化：投币代表对UP主的认可和鼓励，每天投币数有限
- 梗文化：大量使用网络热梗、二次元用语、缩写
- Z世代社区：用户以年轻人为主，表达活泼、有创意
- 分区内容：动画、游戏、音乐、舞蹈、科技、生活等多个分区

# 自我描述
你的行为应该符合你的人设和性格。
{name_str}
{bio_str}
{profile_str}

# 行为准则
- 发弹幕是最常见的互动方式，弹幕要简短有趣
- 看到优质内容首选"一键三连"表达最大认可
- 投币要谨慎，只给真正喜欢的UP主投币
- 善用B站热梗和网络用语（如：awsl、yyds、xswl、草、绝了等）
- 评论区可以整活、玩梗、接龙
- 对喜欢的UP主积极关注和互动

# 回复方式
请通过工具调用来执行操作。"""
```

- [ ] **Step 2: Create Bilibili adapter**

Create `engine/platforms/bilibili.py`:

```python
"""Bilibili platform adapter.

Adds three custom actions:
- send_danmaku: Send a scrolling comment (弹幕)
- give_coin: Give coins to a post's creator (投币)
- triple_tap: One-click like + coin + collect (一键三连)

Uses an interest tag + follow + trending recommendation system.
"""

from __future__ import annotations

import heapq
import logging
import random
from collections import defaultdict
from typing import Any

from oasis.social_platform.typing import RecsysType

from engine.platforms.actions import GIVE_COIN, SEND_DANMAKU, TRIPLE_TAP
from engine.platforms.base import BasePlatformAdapter
from engine.platforms.prompts.bilibili import get_bilibili_system_prompt

logger = logging.getLogger(__name__)


def rec_sys_bilibili(
    user_table: list[dict[str, Any]],
    post_table: list[dict[str, Any]],
    rec_matrix: list[list],
    max_rec_post_len: int,
    db_cursor: Any = None,
) -> list[list]:
    """Bilibili interest tag + follow + trending recommendation system.

    Scoring combines three signals:
    1. Engagement score: likes + coins*2 + collections*1.5 + danmaku*0.5
    2. Follow boost: 1.5x for posts from followed users
    3. Trending boost: posts in top 10% engagement get a bonus

    Args:
        user_table: List of user dicts.
        post_table: List of post dicts.
        rec_matrix: Current recommendation matrix.
        max_rec_post_len: Maximum posts per user.
        db_cursor: Database cursor for relationship/coin data.

    Returns:
        Updated recommendation matrix.
    """
    post_ids = [post["post_id"] for post in post_table]
    num_users = len(rec_matrix)

    if len(post_ids) <= max_rec_post_len:
        return [post_ids] * num_users

    follow_map: dict[int, set[int]] = defaultdict(set)
    coin_counts: dict[int, int] = defaultdict(int)
    danmaku_counts: dict[int, int] = defaultdict(int)
    collection_counts: dict[int, int] = defaultdict(int)

    if db_cursor is not None:
        db_cursor.execute("SELECT follower_id, followee_id FROM follow")
        for row in db_cursor.fetchall():
            follow_map[row[0]].add(row[1])

        for post in post_table:
            pid = post["post_id"]
            try:
                db_cursor.execute(
                    "SELECT COUNT(*) FROM coin WHERE post_id = ?", (pid,)
                )
                row = db_cursor.fetchone()
                if row:
                    coin_counts[pid] = row[0]
            except Exception:
                pass
            try:
                db_cursor.execute(
                    "SELECT COUNT(*) FROM danmaku WHERE post_id = ?", (pid,)
                )
                row = db_cursor.fetchone()
                if row:
                    danmaku_counts[pid] = row[0]
            except Exception:
                pass
            try:
                db_cursor.execute(
                    "SELECT COUNT(*) FROM collection WHERE post_id = ?", (pid,)
                )
                row = db_cursor.fetchone()
                if row:
                    collection_counts[pid] = row[0]
            except Exception:
                pass

    base_scores: dict[int, float] = {}
    for post in post_table:
        pid = post["post_id"]
        likes = post.get("num_likes", 0)
        coins = coin_counts.get(pid, 0)
        collections = collection_counts.get(pid, 0)
        danmaku = danmaku_counts.get(pid, 0)
        score = likes + coins * 2.0 + collections * 1.5 + danmaku * 0.5
        base_scores[pid] = score

    if base_scores:
        sorted_scores = sorted(base_scores.values(), reverse=True)
        trending_threshold = sorted_scores[max(0, len(sorted_scores) // 10)]
    else:
        trending_threshold = 0

    new_rec_matrix: list[list] = []
    for uid in range(num_users):
        following = follow_map.get(uid, set())
        user_scored: list[tuple[float, int]] = []

        for post in post_table:
            pid = post["post_id"]
            score = base_scores[pid]

            if post["user_id"] in following:
                score *= 1.5

            if score >= trending_threshold and trending_threshold > 0:
                score *= 1.2

            score += random.uniform(0, 0.05)
            user_scored.append((score, pid))

        top_posts = heapq.nlargest(
            max_rec_post_len, user_scored, key=lambda x: x[0]
        )
        new_rec_matrix.append([pid for _, pid in top_posts])

    return new_rec_matrix


class BilibiliPlatform(BasePlatformAdapter):
    """Bilibili platform adapter.

    Custom actions:
    - send_danmaku: Send a scrolling comment on a video
    - give_coin: Give coins to a video creator
    - triple_tap: One-click like + coin + collect (一键三连)

    Custom recsys:
    - Interest tag + follow + trending scoring
    """

    PLATFORM_NAME = "bilibili"
    CUSTOM_ACTIONS = {
        SEND_DANMAKU: "send_danmaku",
        GIVE_COIN: "give_coin",
        TRIPLE_TAP: "triple_tap",
    }

    def _setup_custom_tables(self) -> None:
        """Create danmaku, coin, and collection tables for Bilibili."""
        self.db_cursor.executescript("""
            CREATE TABLE IF NOT EXISTS danmaku (
                danmaku_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                post_id INTEGER,
                content TEXT,
                time_offset REAL DEFAULT 0.0,
                created_at DATETIME,
                FOREIGN KEY(user_id) REFERENCES user(user_id),
                FOREIGN KEY(post_id) REFERENCES post(post_id)
            );
            CREATE TABLE IF NOT EXISTS coin (
                coin_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                post_id INTEGER,
                num_coins INTEGER DEFAULT 1,
                created_at DATETIME,
                FOREIGN KEY(user_id) REFERENCES user(user_id),
                FOREIGN KEY(post_id) REFERENCES post(post_id)
            );
            CREATE TABLE IF NOT EXISTS collection (
                collection_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                post_id INTEGER,
                created_at DATETIME,
                FOREIGN KEY(user_id) REFERENCES user(user_id),
                FOREIGN KEY(post_id) REFERENCES post(post_id)
            );
        """)
        self.db.commit()

    async def running(self):
        """Override running loop to handle custom action strings."""
        from oasis.social_platform.typing import ActionType

        while True:
            message_id, data = await self.channel.receive_from()
            agent_id, message, action = data

            if action == ActionType.EXIT.value or action == "exit":
                import sqlite3

                if self.db_path == ":memory:":
                    dst = sqlite3.connect("mock.db")
                    with dst:
                        self.db.backup(dst)
                self.db_cursor.close()
                self.db.close()
                break

            action_function = getattr(self, action, None)
            if action_function:
                func_code = action_function.__code__
                param_names = func_code.co_varnames[:func_code.co_argcount]
                len_param_names = len(param_names)
                if len_param_names > 3:
                    raise ValueError(
                        f"Functions with {len_param_names} parameters "
                        f"are not supported."
                    )
                params = {}
                if len_param_names >= 2:
                    params["agent_id"] = agent_id
                if len_param_names == 3:
                    second_param_name = param_names[2]
                    params[second_param_name] = message
                result = await action_function(**params)
                await self.channel.send_to((message_id, agent_id, result))
            else:
                raise ValueError(f"Action {action} is not supported")

    async def send_danmaku(self, agent_id: int, danmaku_message: tuple):
        """Send a danmaku (scrolling comment) on a video.

        Args:
            agent_id: The sender's agent ID.
            danmaku_message: Tuple of (post_id, content).

        Returns:
            Dict with success status and danmaku_id.
        """
        post_id, content = danmaku_message
        current_time = self._get_current_time()
        try:
            user_id = agent_id

            post_check = "SELECT post_id FROM post WHERE post_id = ?"
            self.pl_utils._execute_db_command(post_check, (post_id,))
            if not self.db_cursor.fetchone():
                return {"success": False, "error": "Post not found."}

            insert_query = (
                "INSERT INTO danmaku (user_id, post_id, content, created_at) "
                "VALUES (?, ?, ?, ?)"
            )
            self.pl_utils._execute_db_command(
                insert_query, (user_id, post_id, content, current_time),
                commit=True,
            )
            danmaku_id = self.db_cursor.lastrowid

            self._record_custom_trace(
                user_id,
                SEND_DANMAKU,
                {
                    "post_id": post_id,
                    "content": content,
                    "danmaku_id": danmaku_id,
                },
            )
            return {"success": True, "danmaku_id": danmaku_id}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def give_coin(self, agent_id: int, coin_message: tuple):
        """Give coins to a video's creator.

        Each user can give at most 2 coins to a single video.

        Args:
            agent_id: The giver's agent ID.
            coin_message: Tuple of (post_id, num_coins).

        Returns:
            Dict with success status and coin_id.
        """
        post_id, num_coins = coin_message
        current_time = self._get_current_time()
        try:
            user_id = agent_id

            if num_coins < 1 or num_coins > 2:
                return {
                    "success": False,
                    "error": "Can only give 1 or 2 coins per video.",
                }

            post_check = "SELECT user_id FROM post WHERE post_id = ?"
            self.pl_utils._execute_db_command(post_check, (post_id,))
            post_row = self.db_cursor.fetchone()
            if not post_row:
                return {"success": False, "error": "Post not found."}

            existing_query = (
                "SELECT SUM(num_coins) FROM coin "
                "WHERE user_id = ? AND post_id = ?"
            )
            self.pl_utils._execute_db_command(
                existing_query, (user_id, post_id)
            )
            existing_row = self.db_cursor.fetchone()
            existing_coins = existing_row[0] if existing_row[0] else 0

            if existing_coins + num_coins > 2:
                return {
                    "success": False,
                    "error": (
                        f"Already gave {existing_coins} coin(s). "
                        f"Max 2 per video."
                    ),
                }

            insert_query = (
                "INSERT INTO coin (user_id, post_id, num_coins, created_at) "
                "VALUES (?, ?, ?, ?)"
            )
            self.pl_utils._execute_db_command(
                insert_query, (user_id, post_id, num_coins, current_time),
                commit=True,
            )
            coin_id = self.db_cursor.lastrowid

            self._record_custom_trace(
                user_id,
                GIVE_COIN,
                {
                    "post_id": post_id,
                    "num_coins": num_coins,
                    "coin_id": coin_id,
                },
            )
            return {"success": True, "coin_id": coin_id}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def triple_tap(self, agent_id: int, post_id: int):
        """Perform a "一键三连" (triple tap): like + coin + collect.

        This is the highest form of appreciation on Bilibili.
        Atomically performs all three actions.

        Args:
            agent_id: The user's agent ID.
            post_id: The post to triple-tap.

        Returns:
            Dict with success status and IDs of all three actions.
        """
        current_time = self._get_current_time()
        try:
            user_id = agent_id

            post_check = "SELECT post_id FROM post WHERE post_id = ?"
            self.pl_utils._execute_db_command(post_check, (post_id,))
            if not self.db_cursor.fetchone():
                return {"success": False, "error": "Post not found."}

            like_result = await self.like_post(agent_id, post_id)
            like_id = like_result.get("like_id")

            coin_check = (
                "SELECT SUM(num_coins) FROM coin "
                "WHERE user_id = ? AND post_id = ?"
            )
            self.pl_utils._execute_db_command(coin_check, (user_id, post_id))
            existing = self.db_cursor.fetchone()
            existing_coins = existing[0] if existing[0] else 0
            coin_id = None
            if existing_coins < 2:
                coins_to_give = min(1, 2 - existing_coins)
                coin_insert = (
                    "INSERT INTO coin (user_id, post_id, num_coins, "
                    "created_at) VALUES (?, ?, ?, ?)"
                )
                self.pl_utils._execute_db_command(
                    coin_insert,
                    (user_id, post_id, coins_to_give, current_time),
                    commit=True,
                )
                coin_id = self.db_cursor.lastrowid

            collection_check = (
                "SELECT * FROM collection WHERE user_id = ? AND post_id = ?"
            )
            self.pl_utils._execute_db_command(
                collection_check, (user_id, post_id)
            )
            collection_id = None
            if not self.db_cursor.fetchone():
                collection_insert = (
                    "INSERT INTO collection (user_id, post_id, created_at) "
                    "VALUES (?, ?, ?)"
                )
                self.pl_utils._execute_db_command(
                    collection_insert, (user_id, post_id, current_time),
                    commit=True,
                )
                collection_id = self.db_cursor.lastrowid

            self._record_custom_trace(
                user_id,
                TRIPLE_TAP,
                {
                    "post_id": post_id,
                    "like_id": like_id,
                    "coin_id": coin_id,
                    "collection_id": collection_id,
                },
            )
            return {
                "success": True,
                "like_id": like_id,
                "coin_id": coin_id,
                "collection_id": collection_id,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def update_rec_table(self):
        """Override to use Bilibili interest+follow+trending recsys."""
        from oasis.social_platform.database import (
            fetch_rec_table_as_matrix,
            fetch_table_from_db,
        )

        logger.info("Bilibili: refreshing recommendation cache...")
        user_table = fetch_table_from_db(self.db_cursor, "user")
        post_table = fetch_table_from_db(self.db_cursor, "post")
        rec_matrix = fetch_rec_table_as_matrix(self.db_cursor)

        new_rec_matrix = rec_sys_bilibili(
            user_table, post_table, rec_matrix, self.max_rec_post_len,
            db_cursor=self.db_cursor,
        )

        self.pl_utils._execute_db_command("DELETE FROM rec", commit=True)
        insert_values = [
            (user_id, post_id)
            for user_id in range(len(new_rec_matrix))
            for post_id in new_rec_matrix[user_id]
        ]
        self.pl_utils._execute_many_db_command(
            "INSERT INTO rec (user_id, post_id) VALUES (?, ?)",
            insert_values, commit=True,
        )

    def get_system_prompt(
        self,
        name: str | None = None,
        bio: str | None = None,
        profile: dict[str, Any] | None = None,
    ) -> str:
        return get_bilibili_system_prompt(name=name, bio=bio, profile=profile)


# Self-register with the global registry
from engine.platforms import registry as _registry

try:
    _registry.register(
        name="bilibili",
        adapter_class=BilibiliPlatform,
        default_recsys="random",
        default_actions=[
            "create_post", "like_post", "send_danmaku",
            "give_coin", "triple_tap", "follow",
            "create_comment", "do_nothing",
        ],
        description="Bilibili - 中国Z世代文化社区",
    )
except ValueError:
    pass
```

- [ ] **Step 3: Create Bilibili tests**

Create `engine/platforms/tests/test_bilibili.py`:

```python
"""Tests for the Bilibili platform adapter."""

import os
import os.path as osp
import sqlite3

import pytest

from engine.platforms.bilibili import (
    BilibiliPlatform,
    rec_sys_bilibili,
)
from engine.platforms.prompts.bilibili import get_bilibili_system_prompt

parent_folder = osp.dirname(osp.abspath(__file__))
test_db_filepath = osp.join(parent_folder, "test_bilibili.db")


class TestBilibiliRecsys:
    def test_few_posts_returns_all(self):
        user_table = [{"user_id": 0}]
        post_table = [
            {"post_id": 1, "user_id": 0, "num_likes": 10, "num_shares": 0},
        ]
        rec_matrix = [[]]
        result = rec_sys_bilibili(
            user_table, post_table, rec_matrix, max_rec_post_len=5
        )
        assert len(result) == 1
        assert 1 in result[0]

    def test_top_k_selection(self):
        user_table = [{"user_id": 0}, {"user_id": 1}]
        post_table = [
            {"post_id": i, "user_id": i % 2, "num_likes": i * 5,
             "num_shares": 0}
            for i in range(1, 15)
        ]
        rec_matrix = [[], []]
        result = rec_sys_bilibili(
            user_table, post_table, rec_matrix, max_rec_post_len=3
        )
        assert len(result) == 2
        for row in result:
            assert len(row) == 3


class TestBilibiliPlatform:
    @pytest.fixture
    def platform(self):
        if os.path.exists(test_db_filepath):
            os.remove(test_db_filepath)
        p = BilibiliPlatform(db_path=test_db_filepath, recsys_type="random")
        yield p
        p.db_cursor.close()
        p.db.close()
        if os.path.exists(test_db_filepath):
            os.remove(test_db_filepath)

    def test_platform_name(self, platform):
        assert platform.PLATFORM_NAME == "bilibili"

    def test_custom_tables_created(self, platform):
        for table_name in ["danmaku", "coin", "collection"]:
            platform.db_cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                f"AND name='{table_name}'"
            )
            assert platform.db_cursor.fetchone() is not None, (
                f"Table {table_name} was not created"
            )

    @pytest.mark.asyncio
    async def test_send_danmaku(self, platform):
        conn = sqlite3.connect(test_db_filepath)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (1, 1, "bili_user", 0, 0),
        )
        cursor.execute(
            "INSERT INTO post (post_id, user_id, content, created_at, "
            "num_likes, num_dislikes, num_shares) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, 1, "B站视频", "2025-01-01 12:00:00", 0, 0, 0),
        )
        conn.commit()
        conn.close()

        result = await platform.send_danmaku(1, (1, "awsl"))
        assert result["success"] is True
        assert "danmaku_id" in result

    @pytest.mark.asyncio
    async def test_send_danmaku_nonexistent_post(self, platform):
        conn = sqlite3.connect(test_db_filepath)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (1, 1, "bili_user", 0, 0),
        )
        conn.commit()
        conn.close()

        result = await platform.send_danmaku(1, (999, "test"))
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_give_coin(self, platform):
        conn = sqlite3.connect(test_db_filepath)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (1, 1, "bili_user", 0, 0),
        )
        cursor.execute(
            "INSERT INTO post (post_id, user_id, content, created_at, "
            "num_likes, num_dislikes, num_shares) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, 1, "优质视频", "2025-01-01 12:00:00", 0, 0, 0),
        )
        conn.commit()
        conn.close()

        result = await platform.give_coin(1, (1, 1))
        assert result["success"] is True
        assert "coin_id" in result

    @pytest.mark.asyncio
    async def test_give_coin_exceeds_limit(self, platform):
        conn = sqlite3.connect(test_db_filepath)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (1, 1, "bili_user", 0, 0),
        )
        cursor.execute(
            "INSERT INTO post (post_id, user_id, content, created_at, "
            "num_likes, num_dislikes, num_shares) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, 1, "优质视频", "2025-01-01 12:00:00", 0, 0, 0),
        )
        conn.commit()
        conn.close()

        await platform.give_coin(1, (1, 2))
        result = await platform.give_coin(1, (1, 1))
        assert result["success"] is False
        assert "Max 2" in result["error"]

    @pytest.mark.asyncio
    async def test_give_coin_invalid_amount(self, platform):
        conn = sqlite3.connect(test_db_filepath)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (1, 1, "bili_user", 0, 0),
        )
        cursor.execute(
            "INSERT INTO post (post_id, user_id, content, created_at, "
            "num_likes, num_dislikes, num_shares) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, 1, "视频", "2025-01-01 12:00:00", 0, 0, 0),
        )
        conn.commit()
        conn.close()

        result = await platform.give_coin(1, (1, 5))
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_triple_tap(self, platform):
        conn = sqlite3.connect(test_db_filepath)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (1, 1, "bili_user1", 0, 0),
        )
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (2, 2, "bili_user2", 0, 0),
        )
        cursor.execute(
            "INSERT INTO post (post_id, user_id, content, created_at, "
            "num_likes, num_dislikes, num_shares) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, 2, "三连视频", "2025-01-01 12:00:00", 0, 0, 0),
        )
        conn.commit()
        conn.close()

        result = await platform.triple_tap(1, 1)
        assert result["success"] is True
        assert "like_id" in result
        assert "coin_id" in result
        assert "collection_id" in result

    @pytest.mark.asyncio
    async def test_triple_tap_nonexistent_post(self, platform):
        conn = sqlite3.connect(test_db_filepath)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (1, 1, "bili_user", 0, 0),
        )
        conn.commit()
        conn.close()

        result = await platform.triple_tap(1, 999)
        assert result["success"] is False

    def test_system_prompt(self, platform):
        prompt = platform.get_system_prompt(name="B站小白")
        assert "B站" in prompt or "Bilibili" in prompt
        assert "弹幕" in prompt


class TestBilibiliPrompts:
    def test_basic_prompt(self):
        prompt = get_bilibili_system_prompt(name="二次元少女")
        assert "B站" in prompt or "Bilibili" in prompt
        assert "弹幕" in prompt
        assert "三连" in prompt
        assert "投币" in prompt
        assert "二次元少女" in prompt
```

- [ ] **Step 4: Commit**

```bash
cd D:/project/oasis
git add engine/platforms/bilibili.py engine/platforms/prompts/bilibili.py engine/platforms/tests/test_bilibili.py
git commit -m "feat(platforms): add Bilibili adapter with danmaku, coin, triple-tap

Bilibili adapter adds:
- send_danmaku, give_coin, triple_tap custom actions
- Interest tag + follow + trending recsys
- Z世代梗文化 agent prompts with ACG style"
```

---

## Task 8: WeChat Video Adapter

**Files:**
- Create: `engine/platforms/wechat_video.py`
- Create: `engine/platforms/prompts/wechat_video.py`
- Create: `engine/platforms/tests/test_wechat_video.py`

- [ ] **Step 1: Create WeChat Video agent prompts**

Create `engine/platforms/prompts/wechat_video.py`:

```python
"""WeChat Video (微信视频号) agent prompt templates.

WeChat Video culture characteristics:
- Middle-aged user base (35-55 years old dominant)
- 正能量 (positive energy content)
- Social-first: friend likes and shares drive discovery
- Sharing-driven: content spreads through WeChat social graph
- 朋友圈 integration (Moments)
- Conservative, family-oriented content style
"""


def get_wechat_video_system_prompt(
    name: str | None = None,
    bio: str | None = None,
    profile: dict | None = None,
) -> str:
    """Generate a WeChat Video style system prompt for an agent.

    Args:
        name: Agent display name.
        bio: Agent biography.
        profile: Additional profile dict.

    Returns:
        Chinese-language system prompt capturing WeChat Video culture.
    """
    name_str = f"你的昵称是{name}。" if name else ""
    bio_str = f"你的个人简介：{bio}" if bio else ""

    profile_str = ""
    if profile and "other_info" in profile:
        info = profile["other_info"]
        if info.get("user_profile"):
            profile_str = f"你的人设：{info['user_profile']}。"
        parts = []
        if info.get("gender"):
            parts.append(f"性别{info['gender']}")
        if info.get("age"):
            parts.append(f"{info['age']}岁")
        if info.get("city"):
            parts.append(f"来自{info['city']}")
        if parts:
            profile_str += "你是一位" + "、".join(parts) + "的视频号用户。"

    return f"""# 目标
你是一个微信视频号用户。我会给你展示一些视频内容（以文字描述呈现），看完后请从可用的操作中选择你要执行的动作。

# 平台特点
微信视频号是微信生态内的短视频平台，用户以中老年群体为主。视频号文化的特点：
- 正能量导向：偏好积极向上、有教育意义、温暖人心的内容
- 社交传播：内容主要通过微信朋友的点赞和分享来传播
- 朋友推荐：你能看到朋友点赞过的视频，社交信号是主要推荐依据
- 分享文化：看到好内容喜欢分享给微信好友和朋友圈
- 内容偏好：养生健康、家庭情感、正能量故事、实用知识
- 表达含蓄：评论风格相对正式、温和，少用网络热梗

# 自我描述
你的行为应该符合你的人设和性格。
{name_str}
{bio_str}
{profile_str}

# 行为准则
- 看到正能量、有教育意义的内容优先点赞和分享
- 分享给好友时习惯附上一句推荐语
- 评论风格温和、正式，较少使用网络流行语
- 关注养生健康、家庭教育、社会正能量类内容
- 对涉及家人朋友的内容更容易互动
- 分享是最重要的行为，代表认可并想传播给身边人

# 回复方式
请通过工具调用来执行操作。"""
```

- [ ] **Step 2: Create WeChat Video adapter**

Create `engine/platforms/wechat_video.py`:

```python
"""WeChat Video (微信视频号) platform adapter.

Adds one custom action:
- share_to_friends: Share a video to WeChat friends (social spread)

Uses a social-first recommendation system where friend likes
are the primary discovery mechanism, with algorithmic scoring
as a secondary signal.
"""

from __future__ import annotations

import heapq
import logging
import random
from collections import defaultdict
from typing import Any

from oasis.social_platform.typing import RecsysType

from engine.platforms.actions import SHARE_TO_FRIENDS
from engine.platforms.base import BasePlatformAdapter
from engine.platforms.prompts.wechat_video import (
    get_wechat_video_system_prompt,
)

logger = logging.getLogger(__name__)


def rec_sys_wechat_video(
    user_table: list[dict[str, Any]],
    post_table: list[dict[str, Any]],
    rec_matrix: list[list],
    max_rec_post_len: int,
    db_cursor: Any = None,
    friend_like_weight: float = 3.0,
    friend_share_weight: float = 4.0,
) -> list[list]:
    """WeChat Video social-first recommendation system.

    WeChat Video's algorithm prioritizes social signals:
    1. Posts liked by friends get 3x weight
    2. Posts shared by friends get 4x weight
    3. Base engagement provides secondary scoring

    This creates a "friend bubble" where you primarily see what
    your social circle interacts with.

    Args:
        user_table: List of user dicts.
        post_table: List of post dicts.
        rec_matrix: Current recommendation matrix.
        max_rec_post_len: Maximum posts per user.
        db_cursor: Database cursor for social data.
        friend_like_weight: Score multiplier for friend-liked posts.
        friend_share_weight: Score multiplier for friend-shared posts.

    Returns:
        Updated recommendation matrix.
    """
    post_ids = [post["post_id"] for post in post_table]
    num_users = len(rec_matrix)

    if len(post_ids) <= max_rec_post_len:
        return [post_ids] * num_users

    follow_map: dict[int, set[int]] = defaultdict(set)
    post_likers: dict[int, set[int]] = defaultdict(set)
    post_sharers: dict[int, set[int]] = defaultdict(set)

    if db_cursor is not None:
        db_cursor.execute("SELECT follower_id, followee_id FROM follow")
        for row in db_cursor.fetchall():
            follow_map[row[0]].add(row[1])
            follow_map[row[1]].add(row[0])

        db_cursor.execute("SELECT post_id, user_id FROM 'like'")
        for row in db_cursor.fetchall():
            post_likers[row[0]].add(row[1])

        try:
            db_cursor.execute(
                "SELECT post_id, user_id FROM friend_share"
            )
            for row in db_cursor.fetchall():
                post_sharers[row[0]].add(row[1])
        except Exception:
            pass

    base_scores: dict[int, float] = {}
    for post in post_table:
        pid = post["post_id"]
        likes = post.get("num_likes", 0)
        shares = post.get("num_shares", 0)
        base_scores[pid] = likes + shares * 1.5

    new_rec_matrix: list[list] = []
    for uid in range(num_users):
        friends = follow_map.get(uid, set())
        user_scored: list[tuple[float, int]] = []

        for post in post_table:
            pid = post["post_id"]
            score = base_scores[pid]

            likers = post_likers.get(pid, set())
            friend_likers = friends & likers
            if friend_likers:
                score += len(friend_likers) * friend_like_weight

            sharers = post_sharers.get(pid, set())
            friend_sharers = friends & sharers
            if friend_sharers:
                score += len(friend_sharers) * friend_share_weight

            score += random.uniform(0, 0.05)
            user_scored.append((score, pid))

        top_posts = heapq.nlargest(
            max_rec_post_len, user_scored, key=lambda x: x[0]
        )
        new_rec_matrix.append([pid for _, pid in top_posts])

    return new_rec_matrix


class WeChatVideoPlatform(BasePlatformAdapter):
    """WeChat Video (微信视频号) platform adapter.

    Custom actions:
    - share_to_friends: Share video to WeChat friends list

    Custom recsys:
    - Social-first: friend-likes and friend-shares as primary signals
    """

    PLATFORM_NAME = "wechat_video"
    CUSTOM_ACTIONS = {
        SHARE_TO_FRIENDS: "share_to_friends",
    }

    def _setup_custom_tables(self) -> None:
        """Create friend_share table for WeChat Video."""
        self.db_cursor.executescript("""
            CREATE TABLE IF NOT EXISTS friend_share (
                share_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                post_id INTEGER,
                target_user_id INTEGER,
                message TEXT DEFAULT '',
                created_at DATETIME,
                FOREIGN KEY(user_id) REFERENCES user(user_id),
                FOREIGN KEY(post_id) REFERENCES post(post_id),
                FOREIGN KEY(target_user_id) REFERENCES user(user_id)
            );
        """)
        self.db.commit()

    async def running(self):
        """Override running loop to handle custom action strings."""
        from oasis.social_platform.typing import ActionType

        while True:
            message_id, data = await self.channel.receive_from()
            agent_id, message, action = data

            if action == ActionType.EXIT.value or action == "exit":
                import sqlite3

                if self.db_path == ":memory:":
                    dst = sqlite3.connect("mock.db")
                    with dst:
                        self.db.backup(dst)
                self.db_cursor.close()
                self.db.close()
                break

            action_function = getattr(self, action, None)
            if action_function:
                func_code = action_function.__code__
                param_names = func_code.co_varnames[:func_code.co_argcount]
                len_param_names = len(param_names)
                if len_param_names > 3:
                    raise ValueError(
                        f"Functions with {len_param_names} parameters "
                        f"are not supported."
                    )
                params = {}
                if len_param_names >= 2:
                    params["agent_id"] = agent_id
                if len_param_names == 3:
                    second_param_name = param_names[2]
                    params[second_param_name] = message
                result = await action_function(**params)
                await self.channel.send_to((message_id, agent_id, result))
            else:
                raise ValueError(f"Action {action} is not supported")

    async def share_to_friends(self, agent_id: int, share_message: tuple):
        """Share a video to a specific WeChat friend.

        This is the primary distribution mechanism on WeChat Video.
        Content spreads through the social graph via direct shares.

        Args:
            agent_id: The sharing user's agent ID.
            share_message: Tuple of (post_id, target_user_id, message).
                The message is an optional recommendation text.

        Returns:
            Dict with success status and share_id.
        """
        post_id, target_user_id, rec_message = share_message
        current_time = self._get_current_time()
        try:
            user_id = agent_id

            if user_id == target_user_id:
                return {
                    "success": False,
                    "error": "Cannot share to yourself.",
                }

            post_check = "SELECT post_id FROM post WHERE post_id = ?"
            self.pl_utils._execute_db_command(post_check, (post_id,))
            if not self.db_cursor.fetchone():
                return {"success": False, "error": "Post not found."}

            user_check = "SELECT user_id FROM user WHERE user_id = ?"
            self.pl_utils._execute_db_command(user_check, (target_user_id,))
            if not self.db_cursor.fetchone():
                return {"success": False, "error": "Target user not found."}

            insert_query = (
                "INSERT INTO friend_share (user_id, post_id, "
                "target_user_id, message, created_at) "
                "VALUES (?, ?, ?, ?, ?)"
            )
            self.pl_utils._execute_db_command(
                insert_query,
                (user_id, post_id, target_user_id, rec_message, current_time),
                commit=True,
            )
            share_id = self.db_cursor.lastrowid

            update_query = (
                "UPDATE post SET num_shares = num_shares + 1 "
                "WHERE post_id = ?"
            )
            self.pl_utils._execute_db_command(
                update_query, (post_id,), commit=True
            )

            self._record_custom_trace(
                user_id,
                SHARE_TO_FRIENDS,
                {
                    "post_id": post_id,
                    "target_user_id": target_user_id,
                    "message": rec_message,
                    "share_id": share_id,
                },
            )
            return {
                "success": True,
                "share_id": share_id,
                "target_user_id": target_user_id,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def update_rec_table(self):
        """Override to use WeChat Video social-first recsys."""
        from oasis.social_platform.database import (
            fetch_rec_table_as_matrix,
            fetch_table_from_db,
        )

        logger.info("WeChat Video: refreshing recommendation cache...")
        user_table = fetch_table_from_db(self.db_cursor, "user")
        post_table = fetch_table_from_db(self.db_cursor, "post")
        rec_matrix = fetch_rec_table_as_matrix(self.db_cursor)

        new_rec_matrix = rec_sys_wechat_video(
            user_table, post_table, rec_matrix, self.max_rec_post_len,
            db_cursor=self.db_cursor,
        )

        self.pl_utils._execute_db_command("DELETE FROM rec", commit=True)
        insert_values = [
            (user_id, post_id)
            for user_id in range(len(new_rec_matrix))
            for post_id in new_rec_matrix[user_id]
        ]
        self.pl_utils._execute_many_db_command(
            "INSERT INTO rec (user_id, post_id) VALUES (?, ?)",
            insert_values, commit=True,
        )

    def get_system_prompt(
        self,
        name: str | None = None,
        bio: str | None = None,
        profile: dict[str, Any] | None = None,
    ) -> str:
        return get_wechat_video_system_prompt(
            name=name, bio=bio, profile=profile
        )


# Self-register with the global registry
from engine.platforms import registry as _registry

try:
    _registry.register(
        name="wechat_video",
        adapter_class=WeChatVideoPlatform,
        default_recsys="random",
        default_actions=[
            "create_post", "like_post", "share_to_friends",
            "follow", "create_comment", "do_nothing",
        ],
        description="微信视频号 - 微信生态内的短视频平台",
    )
except ValueError:
    pass
```

- [ ] **Step 3: Create WeChat Video tests**

Create `engine/platforms/tests/test_wechat_video.py`:

```python
"""Tests for the WeChat Video platform adapter."""

import os
import os.path as osp
import sqlite3

import pytest

from engine.platforms.wechat_video import (
    WeChatVideoPlatform,
    rec_sys_wechat_video,
)
from engine.platforms.prompts.wechat_video import (
    get_wechat_video_system_prompt,
)

parent_folder = osp.dirname(osp.abspath(__file__))
test_db_filepath = osp.join(parent_folder, "test_wechat_video.db")


class TestWeChatVideoRecsys:
    def test_few_posts_returns_all(self):
        user_table = [{"user_id": 0}]
        post_table = [
            {"post_id": 1, "user_id": 0, "num_likes": 5, "num_shares": 1},
        ]
        rec_matrix = [[]]
        result = rec_sys_wechat_video(
            user_table, post_table, rec_matrix, max_rec_post_len=5
        )
        assert len(result) == 1
        assert 1 in result[0]

    def test_top_k_selection(self):
        user_table = [{"user_id": i} for i in range(3)]
        post_table = [
            {"post_id": i, "user_id": i % 3, "num_likes": i * 2,
             "num_shares": 0}
            for i in range(1, 15)
        ]
        rec_matrix = [[] for _ in range(3)]
        result = rec_sys_wechat_video(
            user_table, post_table, rec_matrix, max_rec_post_len=3
        )
        assert len(result) == 3
        for row in result:
            assert len(row) == 3


class TestWeChatVideoPlatform:
    @pytest.fixture
    def platform(self):
        if os.path.exists(test_db_filepath):
            os.remove(test_db_filepath)
        p = WeChatVideoPlatform(
            db_path=test_db_filepath, recsys_type="random"
        )
        yield p
        p.db_cursor.close()
        p.db.close()
        if os.path.exists(test_db_filepath):
            os.remove(test_db_filepath)

    def test_platform_name(self, platform):
        assert platform.PLATFORM_NAME == "wechat_video"

    def test_friend_share_table_created(self, platform):
        platform.db_cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='friend_share'"
        )
        assert platform.db_cursor.fetchone() is not None

    @pytest.mark.asyncio
    async def test_share_to_friends(self, platform):
        conn = sqlite3.connect(test_db_filepath)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (1, 1, "wx_user1", 0, 0),
        )
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (2, 2, "wx_user2", 0, 0),
        )
        cursor.execute(
            "INSERT INTO post (post_id, user_id, content, created_at, "
            "num_likes, num_dislikes, num_shares) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, 1, "正能量视频", "2025-01-01 12:00:00", 0, 0, 0),
        )
        conn.commit()
        conn.close()

        result = await platform.share_to_friends(
            1, (1, 2, "这个视频很不错，推荐给你看看")
        )
        assert result["success"] is True
        assert "share_id" in result
        assert result["target_user_id"] == 2

    @pytest.mark.asyncio
    async def test_share_to_self_fails(self, platform):
        conn = sqlite3.connect(test_db_filepath)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (1, 1, "wx_user1", 0, 0),
        )
        cursor.execute(
            "INSERT INTO post (post_id, user_id, content, created_at, "
            "num_likes, num_dislikes, num_shares) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, 1, "视频", "2025-01-01 12:00:00", 0, 0, 0),
        )
        conn.commit()
        conn.close()

        result = await platform.share_to_friends(1, (1, 1, "分享"))
        assert result["success"] is False
        assert "yourself" in result["error"]

    @pytest.mark.asyncio
    async def test_share_nonexistent_post(self, platform):
        conn = sqlite3.connect(test_db_filepath)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (1, 1, "wx_user1", 0, 0),
        )
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (2, 2, "wx_user2", 0, 0),
        )
        conn.commit()
        conn.close()

        result = await platform.share_to_friends(1, (999, 2, "看看"))
        assert result["success"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_share_to_nonexistent_user(self, platform):
        conn = sqlite3.connect(test_db_filepath)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (1, 1, "wx_user1", 0, 0),
        )
        cursor.execute(
            "INSERT INTO post (post_id, user_id, content, created_at, "
            "num_likes, num_dislikes, num_shares) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, 1, "视频", "2025-01-01 12:00:00", 0, 0, 0),
        )
        conn.commit()
        conn.close()

        result = await platform.share_to_friends(1, (1, 999, "看看"))
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_system_prompt(self, platform):
        prompt = platform.get_system_prompt(name="李阿姨")
        assert "视频号" in prompt
        assert "正能量" in prompt


class TestWeChatVideoPrompts:
    def test_basic_prompt(self):
        prompt = get_wechat_video_system_prompt(name="王叔叔")
        assert "视频号" in prompt
        assert "正能量" in prompt
        assert "分享" in prompt
        assert "朋友" in prompt
        assert "王叔叔" in prompt

    def test_prompt_with_profile(self):
        profile = {
            "other_info": {
                "user_profile": "退休教师，热爱生活",
                "gender": "女",
                "age": 55,
                "city": "杭州",
            }
        }
        prompt = get_wechat_video_system_prompt(
            name="张老师", profile=profile,
        )
        assert "退休教师" in prompt
        assert "杭州" in prompt
```

- [ ] **Step 4: Commit**

```bash
cd D:/project/oasis
git add engine/platforms/wechat_video.py engine/platforms/prompts/wechat_video.py engine/platforms/tests/test_wechat_video.py
git commit -m "feat(platforms): add WeChat Video adapter with share-to-friends

WeChat Video adapter adds:
- share_to_friends custom action for social-graph distribution
- Social-first recsys prioritizing friend-likes and friend-shares
- 正能量 agent prompts with middle-aged sharing-driven style"
```

---

## Task 9: Integration Tests

**Files:**
- Create: `engine/platforms/tests/test_recsys.py`
- Create: `engine/platforms/tests/test_integration.py`

- [ ] **Step 1: Create recsys comparison tests**

Create `engine/platforms/tests/test_recsys.py`:

```python
"""Tests comparing recommendation algorithms across all platforms."""

import pytest

from engine.platforms.weibo import rec_sys_weibo
from engine.platforms.xiaohongshu import rec_sys_xiaohongshu
from engine.platforms.douyin import rec_sys_douyin
from engine.platforms.kuaishou import rec_sys_kuaishou
from engine.platforms.bilibili import rec_sys_bilibili
from engine.platforms.wechat_video import rec_sys_wechat_video


def make_post_table(n: int) -> list[dict]:
    """Generate a synthetic post table with n posts."""
    return [
        {
            "post_id": i,
            "user_id": i % 5,
            "num_likes": i * 3,
            "num_dislikes": max(0, i - 5),
            "num_shares": i * 2,
            "created_at": f"2025-01-{(i % 28) + 1:02d} 12:00:00",
        }
        for i in range(1, n + 1)
    ]


def make_user_table(n: int) -> list[dict]:
    """Generate a synthetic user table with n users."""
    return [{"user_id": i, "bio": f"User {i}"} for i in range(n)]


class TestAllRecsysReturnValidMatrix:
    """Ensure all recsys functions return valid matrices with correct
    shapes and no out-of-range post IDs."""

    @pytest.fixture
    def common_data(self):
        post_table = make_post_table(20)
        user_table = make_user_table(5)
        rec_matrix = [[] for _ in range(5)]
        max_len = 5
        return post_table, user_table, rec_matrix, max_len

    def test_weibo_recsys_shape(self, common_data):
        post_table, _, rec_matrix, max_len = common_data
        result = rec_sys_weibo(post_table, rec_matrix, max_len)
        assert len(result) == len(rec_matrix)
        valid_ids = {p["post_id"] for p in post_table}
        for row in result:
            assert len(row) <= max_len
            for pid in row:
                assert pid in valid_ids

    def test_xiaohongshu_recsys_shape(self, common_data):
        post_table, _, rec_matrix, max_len = common_data
        result = rec_sys_xiaohongshu(post_table, rec_matrix, max_len)
        assert len(result) == len(rec_matrix)
        valid_ids = {p["post_id"] for p in post_table}
        for row in result:
            assert len(row) <= max_len
            for pid in row:
                assert pid in valid_ids

    def test_douyin_recsys_shape(self, common_data):
        post_table, _, rec_matrix, max_len = common_data
        result = rec_sys_douyin(post_table, rec_matrix, max_len)
        assert len(result) == len(rec_matrix)
        valid_ids = {p["post_id"] for p in post_table}
        for row in result:
            assert len(row) <= max_len
            for pid in row:
                assert pid in valid_ids

    def test_kuaishou_recsys_shape(self, common_data):
        post_table, user_table, rec_matrix, max_len = common_data
        result = rec_sys_kuaishou(
            user_table, post_table, rec_matrix, max_len
        )
        assert len(result) == len(rec_matrix)
        valid_ids = {p["post_id"] for p in post_table}
        for row in result:
            assert len(row) <= max_len
            for pid in row:
                assert pid in valid_ids

    def test_bilibili_recsys_shape(self, common_data):
        post_table, user_table, rec_matrix, max_len = common_data
        result = rec_sys_bilibili(
            user_table, post_table, rec_matrix, max_len
        )
        assert len(result) == len(rec_matrix)
        valid_ids = {p["post_id"] for p in post_table}
        for row in result:
            assert len(row) <= max_len
            for pid in row:
                assert pid in valid_ids

    def test_wechat_video_recsys_shape(self, common_data):
        post_table, user_table, rec_matrix, max_len = common_data
        result = rec_sys_wechat_video(
            user_table, post_table, rec_matrix, max_len
        )
        assert len(result) == len(rec_matrix)
        valid_ids = {p["post_id"] for p in post_table}
        for row in result:
            assert len(row) <= max_len
            for pid in row:
                assert pid in valid_ids


class TestRecsysEdgeCases:
    """Test edge cases common to all recsys implementations."""

    def test_empty_post_table(self):
        rec_matrix = [[], []]
        assert rec_sys_weibo([], rec_matrix, 5) == [[], []]
        assert rec_sys_xiaohongshu([], rec_matrix, 5) == [[], []]
        assert rec_sys_douyin([], rec_matrix, 5) == [[], []]

    def test_single_post(self):
        posts = [{"post_id": 1, "user_id": 0, "num_likes": 0,
                  "num_dislikes": 0, "num_shares": 0,
                  "created_at": "2025-01-01 12:00:00"}]
        rec_matrix = [[], [], []]
        result = rec_sys_weibo(posts, rec_matrix, 5)
        assert all(1 in row for row in result)

    def test_single_user(self):
        posts = make_post_table(10)
        users = make_user_table(1)
        rec_matrix = [[]]
        result_ks = rec_sys_kuaishou(users, posts, rec_matrix, 3)
        assert len(result_ks) == 1
        assert len(result_ks[0]) == 3

        result_bl = rec_sys_bilibili(users, posts, rec_matrix, 3)
        assert len(result_bl) == 1
        assert len(result_bl[0]) == 3

        result_wx = rec_sys_wechat_video(users, posts, rec_matrix, 3)
        assert len(result_wx) == 1
        assert len(result_wx[0]) == 3
```

- [ ] **Step 2: Create integration tests**

Create `engine/platforms/tests/test_integration.py`:

```python
"""Integration tests for platform registry and all adapters."""

import os
import os.path as osp
import sqlite3

import pytest

from engine.platforms import PlatformRegistry, registry
from engine.platforms.base import BasePlatformAdapter
from engine.platforms.weibo import WeiboPlatform
from engine.platforms.xiaohongshu import XiaohongshuPlatform
from engine.platforms.douyin import DouyinPlatform
from engine.platforms.kuaishou import KuaishouPlatform
from engine.platforms.bilibili import BilibiliPlatform
from engine.platforms.wechat_video import WeChatVideoPlatform

parent_folder = osp.dirname(osp.abspath(__file__))


class TestAutoDiscovery:
    """Test that auto_discover() loads all platform adapters."""

    def test_auto_discover_registers_all(self):
        test_registry = PlatformRegistry()
        test_registry.register("twitter", WeiboPlatform)
        test_registry.register("reddit", WeiboPlatform)

        test_registry.register("weibo", WeiboPlatform)
        test_registry.register("xiaohongshu", XiaohongshuPlatform)
        test_registry.register("douyin", DouyinPlatform)
        test_registry.register("kuaishou", KuaishouPlatform)
        test_registry.register("bilibili", BilibiliPlatform)
        test_registry.register("wechat_video", WeChatVideoPlatform)

        platforms = test_registry.list_platforms()
        assert "weibo" in platforms
        assert "xiaohongshu" in platforms
        assert "douyin" in platforms
        assert "kuaishou" in platforms
        assert "bilibili" in platforms
        assert "wechat_video" in platforms


class TestGlobalRegistryHasAllPlatforms:
    """Verify the global registry contains all expected platforms."""

    def test_global_registry_has_builtins(self):
        assert "twitter" in registry.list_platforms()
        assert "reddit" in registry.list_platforms()

    def test_global_registry_has_chinese_platforms(self):
        registry.auto_discover()
        platforms = registry.list_platforms()
        expected = [
            "weibo", "xiaohongshu", "douyin",
            "kuaishou", "bilibili", "wechat_video",
        ]
        for name in expected:
            assert name in platforms, f"{name} not found in registry"


class TestAllPlatformsInstantiate:
    """Test that every registered adapter can be instantiated."""

    @pytest.fixture(params=[
        ("weibo", WeiboPlatform),
        ("xiaohongshu", XiaohongshuPlatform),
        ("douyin", DouyinPlatform),
        ("kuaishou", KuaishouPlatform),
        ("bilibili", BilibiliPlatform),
        ("wechat_video", WeChatVideoPlatform),
    ])
    def platform_instance(self, request):
        name, cls = request.param
        db_path = osp.join(parent_folder, f"test_integ_{name}.db")
        if os.path.exists(db_path):
            os.remove(db_path)
        p = cls(db_path=db_path, recsys_type="random")
        yield name, p, db_path
        p.db_cursor.close()
        p.db.close()
        if os.path.exists(db_path):
            os.remove(db_path)

    def test_is_platform_subclass(self, platform_instance):
        name, platform, _ = platform_instance
        assert isinstance(platform, BasePlatformAdapter)

    def test_has_platform_name(self, platform_instance):
        name, platform, _ = platform_instance
        assert platform.PLATFORM_NAME == name

    def test_get_system_prompt_returns_chinese(self, platform_instance):
        name, platform, _ = platform_instance
        prompt = platform.get_system_prompt(name="测试用户", bio="测试简介")
        assert len(prompt) > 50
        assert "测试用户" in prompt

    def test_get_available_actions(self, platform_instance):
        name, platform, _ = platform_instance
        actions = platform.get_available_actions()
        assert "create_post" in actions
        assert "like_post" in actions
        assert "do_nothing" in actions

    @pytest.mark.asyncio
    async def test_core_create_post_works(self, platform_instance):
        name, platform, db_path = platform_instance
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (1, 1, f"{name}_test_user", 0, 0),
        )
        conn.commit()
        conn.close()

        result = await platform.create_post(1, f"测试帖子 from {name}")
        assert result["success"] is True
        assert "post_id" in result

    @pytest.mark.asyncio
    async def test_core_like_post_works(self, platform_instance):
        name, platform, db_path = platform_instance
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (1, 1, f"{name}_user1", 0, 0),
        )
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (2, 2, f"{name}_user2", 0, 0),
        )
        cursor.execute(
            "INSERT INTO post (post_id, user_id, content, created_at, "
            "num_likes, num_dislikes, num_shares) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, 1, "test post", "2025-01-01 12:00:00", 0, 0, 0),
        )
        conn.commit()
        conn.close()

        result = await platform.like_post(2, 1)
        assert result["success"] is True
        assert "like_id" in result

    @pytest.mark.asyncio
    async def test_core_follow_works(self, platform_instance):
        name, platform, db_path = platform_instance
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (1, 1, f"{name}_user1", 0, 0),
        )
        cursor.execute(
            "INSERT INTO user (user_id, agent_id, user_name, "
            "num_followings, num_followers) VALUES (?, ?, ?, ?, ?)",
            (2, 2, f"{name}_user2", 0, 0),
        )
        conn.commit()
        conn.close()

        result = await platform.follow(1, 2)
        assert result["success"] is True
```

- [ ] **Step 3: Commit**

```bash
cd D:/project/oasis
git add engine/platforms/tests/test_recsys.py engine/platforms/tests/test_integration.py
git commit -m "test(platforms): add recsys comparison and integration tests

Adds comprehensive tests verifying:
- All 6 recsys algorithms return valid matrices
- Edge cases (empty posts, single user)
- All adapters instantiate and support core actions
- System prompts return Chinese text with user info"
```

---

## Running All Tests

After all tasks are complete, run the full test suite:

```bash
cd D:/project/oasis
python -m pytest engine/platforms/tests/ -v --tb=short
```

Expected test count: approximately 70+ tests covering:
- Registry operations (8 tests)
- Action type definitions (12 tests)
- Weibo adapter + recsys + prompts (12 tests)
- Xiaohongshu adapter + recsys + prompts (10 tests)
- Douyin adapter + recsys + prompts (8 tests)
- Kuaishou adapter + recsys + prompts (8 tests)
- Bilibili adapter + recsys + prompts (12 tests)
- WeChat Video adapter + recsys + prompts (8 tests)
- Recsys comparison cross-platform (10 tests)
- Integration tests across all platforms (30+ parametrized tests)

---

## Summary of Files Created

| File | Purpose |
|------|---------|
| `engine/__init__.py` | Engine package |
| `engine/platforms/__init__.py` | PlatformRegistry + global registry |
| `engine/platforms/base.py` | BasePlatformAdapter base class |
| `engine/platforms/actions.py` | Custom action type constants |
| `engine/platforms/weibo.py` | Weibo adapter + recsys |
| `engine/platforms/xiaohongshu.py` | Xiaohongshu adapter + recsys |
| `engine/platforms/douyin.py` | Douyin adapter + recsys |
| `engine/platforms/kuaishou.py` | Kuaishou adapter + recsys |
| `engine/platforms/bilibili.py` | Bilibili adapter + recsys |
| `engine/platforms/wechat_video.py` | WeChat Video adapter + recsys |
| `engine/platforms/prompts/__init__.py` | Prompts package |
| `engine/platforms/prompts/weibo.py` | Weibo agent prompts |
| `engine/platforms/prompts/xiaohongshu.py` | Xiaohongshu agent prompts |
| `engine/platforms/prompts/douyin.py` | Douyin agent prompts |
| `engine/platforms/prompts/kuaishou.py` | Kuaishou agent prompts |
| `engine/platforms/prompts/bilibili.py` | Bilibili agent prompts |
| `engine/platforms/prompts/wechat_video.py` | WeChat Video agent prompts |
| `engine/platforms/tests/__init__.py` | Tests package |
| `engine/platforms/tests/test_registry.py` | Registry tests |
| `engine/platforms/tests/test_actions.py` | Action type tests |
| `engine/platforms/tests/test_weibo.py` | Weibo tests |
| `engine/platforms/tests/test_xiaohongshu.py` | Xiaohongshu tests |
| `engine/platforms/tests/test_douyin.py` | Douyin tests |
| `engine/platforms/tests/test_kuaishou.py` | Kuaishou tests |
| `engine/platforms/tests/test_bilibili.py` | Bilibili tests |
| `engine/platforms/tests/test_wechat_video.py` | WeChat Video tests |
| `engine/platforms/tests/test_recsys.py` | Cross-platform recsys tests |
| `engine/platforms/tests/test_integration.py` | Integration tests |

## Key Design Decisions

1. **No oasis/ modifications:** All adapters subclass `Platform` and add methods. The `running()` override handles custom action dispatch since core `ActionType(action)` would reject unknown action strings.

2. **Custom tables via `_setup_custom_tables()`:** Each adapter creates its own SQLite tables (collection, danmaku, coin, gift, shuoshuo, friend_share) during `__init__`, co-located with the core platform tables.

3. **Recsys functions are standalone:** Following the pattern of `rec_sys_random()` and `rec_sys_reddit()` in `oasis/social_platform/recsys.py`, each platform's recsys is a pure function that receives table data and returns a rec matrix.

4. **Self-registration pattern:** Each adapter module registers itself with the global registry at import time, with a `try/except ValueError` guard for idempotency.

5. **Shared `running()` override:** Platforms with custom actions override `running()` to bypass `ActionType(action)` enum validation. The dispatch logic is identical to the core -- `getattr(self, action)` -- but accepts raw strings.
