# 万象 WANXIANG · M0-A 三层动作空间与平台契约层 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立三层动作空间（L1 决策 / L2 通用社交 / L3 平台方言）与平台插件契约层的纯数据/逻辑骨架——不接 LLM、不接数据库、不改 OASIS，先把决策固化为可单元测试的代码。

**Architecture:** 纯 Python 契约层。用 `@dataclass` 定义动作元数据与三档模式枚举；用声明式 YAML 定义平台方言（Twitter/Reddit/小红书/抖音/微信），由一个 `DialectLoader` 解析并按"L2 抽象动作 → L3 平台别名/启用/关系语义"解析；用 `SimulationMode` 校验三档递进组合（L1 / L1+L2 / L1+L2+L3，不可跳层）。所有逻辑可在无外部依赖下用 pytest 测试。

**Tech Stack:** Python 3.10+, dataclasses, PyYAML, pytest（沿用仓库现有 `poetry run pytest`）。

这是整个项目的**第一个计划**（对应 spec §5 动作空间 + §3.1 的 `actions/` 目录）。后续计划：M0-B（把 OASIS `platform.py` 业务逻辑迁入 dialect 执行体）、M1（造人+模拟主链）等，各自独立成计划。

---

## 文件结构

本计划新建一个独立的顶层包 `wanxiang/`（与 `oasis/` 平级，闭源业务代码起点；spec §3.1）。本计划只建 `wanxiang/actions/` 子树和对应测试，不触碰 `oasis/`。

- `wanxiang/__init__.py` — 包初始化（空）
- `wanxiang/actions/__init__.py` — 导出公共类型
- `wanxiang/actions/layers.py` — `ActionLayer` 枚举（L1/L2/L3）与 `SimulationMode` 枚举（三档）+ 组合校验
- `wanxiang/actions/l1_decision.py` — L1 决策响应动作定义（评分/选择/点击概率/态度/愿付价格）
- `wanxiang/actions/l2_social.py` — L2 通用社交抽象动作定义（发布/转发/点赞/反馈/评论/关注/收藏/私信/屏蔽）
- `wanxiang/actions/dialect.py` — `PlatformDialect` 数据类 + `DialectLoader`（解析 L3 yaml，解析抽象动作→平台具体形态）
- `wanxiang/actions/l3_dialects/twitter.yaml`
- `wanxiang/actions/l3_dialects/reddit.yaml`
- `wanxiang/actions/l3_dialects/xiaohongshu.yaml`
- `wanxiang/actions/l3_dialects/douyin.yaml`
- `wanxiang/actions/l3_dialects/wechat.yaml`
- `test/wanxiang/__init__.py`
- `test/wanxiang/conftest.py` — 把项目根加入 sys.path（沿用 `test/conftest.py` 模式）
- `test/wanxiang/test_layers.py`
- `test/wanxiang/test_l1_decision.py`
- `test/wanxiang/test_l2_social.py`
- `test/wanxiang/test_dialect.py`

---

## Task 0: 准备依赖与包骨架

**Files:**
- Create: `wanxiang/__init__.py`
- Create: `wanxiang/actions/__init__.py`
- Create: `test/wanxiang/__init__.py`
- Create: `test/wanxiang/conftest.py`

- [ ] **Step 1: 确认 PyYAML 在环境中可用**

Run: `poetry run python -c "import yaml; print('yaml', yaml.__version__)"`
Expected: 打印出版本号（如 `yaml 6.0.x`）。若报 `ModuleNotFoundError`，执行 `poetry add pyyaml` 后重试。

- [ ] **Step 2: 创建包初始化文件**

`wanxiang/__init__.py`（写入版权头 + 版本号，沿用 oasis 风格）：

```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the "License");
# (see oasis/ for the upstream OASIS Apache 2.0 components this builds on)
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
__version__ = "0.0.1"
```

`wanxiang/actions/__init__.py`：

```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
from wanxiang.actions.layers import ActionLayer, SimulationMode
from wanxiang.actions.dialect import PlatformDialect, DialectLoader

__all__ = ["ActionLayer", "SimulationMode", "PlatformDialect", "DialectLoader"]
```

`test/wanxiang/__init__.py`：空文件（内容为一行注释 `# wanxiang tests`）。

- [ ] **Step 3: 创建测试 conftest（把项目根加入 sys.path）**

`test/wanxiang/conftest.py`：

```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import os
import sys

# Add the project root directory to sys.path so `import wanxiang` works
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
sys.path.insert(0, root_path)
```

- [ ] **Step 4: 验证包可导入（占位，layers 尚未建，预期失败）**

Run: `poetry run python -c "import wanxiang; print(wanxiang.__version__)"`
Expected: 打印 `0.0.1`。（注意：`wanxiang/actions/__init__.py` 此时 import layers/dialect 会失败，所以本步只导入顶层 `wanxiang`，不导入 `wanxiang.actions`。）

- [ ] **Step 5: Commit**

```bash
git add wanxiang/__init__.py test/wanxiang/__init__.py test/wanxiang/conftest.py
git commit -m "feat(wanxiang): scaffold package and test conftest"
```

> 注意：暂不提交 `wanxiang/actions/__init__.py`（它依赖后续任务的模块）。它在 Task 3 完成后随 dialect 一起提交。

---

## Task 1: ActionLayer 与 SimulationMode（三档递进组合校验）

实现 spec §5.2：三档 `L1` / `L1+L2` / `L1+L2+L3`，**不可跳层**。

**Files:**
- Create: `wanxiang/actions/layers.py`
- Test: `test/wanxiang/test_layers.py`

- [ ] **Step 1: 写失败测试**

`test/wanxiang/test_layers.py`：

```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import pytest

from wanxiang.actions.layers import ActionLayer, SimulationMode


def test_action_layer_values():
    assert ActionLayer.L1_DECISION.value == 1
    assert ActionLayer.L2_SOCIAL.value == 2
    assert ActionLayer.L3_PLATFORM.value == 3


def test_mode_decision_only_includes_only_l1():
    mode = SimulationMode.DECISION_ONLY
    assert mode.active_layers() == [ActionLayer.L1_DECISION]


def test_mode_social_includes_l1_and_l2():
    mode = SimulationMode.SOCIAL
    assert mode.active_layers() == [ActionLayer.L1_DECISION, ActionLayer.L2_SOCIAL]


def test_mode_platform_includes_all_three():
    mode = SimulationMode.PLATFORM
    assert mode.active_layers() == [
        ActionLayer.L1_DECISION,
        ActionLayer.L2_SOCIAL,
        ActionLayer.L3_PLATFORM,
    ]


def test_platform_mode_requires_platform_name():
    # platform 档必须带 platform 名；其它档不需要
    assert SimulationMode.PLATFORM.requires_platform() is True
    assert SimulationMode.SOCIAL.requires_platform() is False
    assert SimulationMode.DECISION_ONLY.requires_platform() is False


def test_from_string_parses_canonical_names():
    assert SimulationMode.from_string("decision_only") is SimulationMode.DECISION_ONLY
    assert SimulationMode.from_string("social") is SimulationMode.SOCIAL
    assert SimulationMode.from_string("platform") is SimulationMode.PLATFORM


def test_from_string_rejects_unknown():
    with pytest.raises(ValueError, match="unknown simulation mode"):
        SimulationMode.from_string("l1_l3")  # 跳层组合不存在
```

- [ ] **Step 2: 运行测试确认失败**

Run: `poetry run pytest test/wanxiang/test_layers.py -v`
Expected: FAIL，错误为 `ModuleNotFoundError: No module named 'wanxiang.actions.layers'`

- [ ] **Step 3: 实现 layers.py**

`wanxiang/actions/layers.py`：

```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""三层动作空间与三档模拟模式定义。

设计见 spec §5：
- L1 决策响应（平台无关，Aaru 路线）
- L2 通用社交（OASIS 内核，跨平台抽象语义）
- L3 平台方言（国内外差异，声明式映射）

三档递进组合，不可跳层：DECISION_ONLY=L1 / SOCIAL=L1+L2 / PLATFORM=L1+L2+L3。
"""
from __future__ import annotations

from enum import Enum


class ActionLayer(Enum):
    L1_DECISION = 1
    L2_SOCIAL = 2
    L3_PLATFORM = 3


class SimulationMode(Enum):
    DECISION_ONLY = "decision_only"  # L1
    SOCIAL = "social"                # L1 + L2
    PLATFORM = "platform"            # L1 + L2 + L3

    def active_layers(self) -> list[ActionLayer]:
        """返回该档启用的层，逐层叠加，不可跳层。"""
        if self is SimulationMode.DECISION_ONLY:
            return [ActionLayer.L1_DECISION]
        if self is SimulationMode.SOCIAL:
            return [ActionLayer.L1_DECISION, ActionLayer.L2_SOCIAL]
        # PLATFORM
        return [
            ActionLayer.L1_DECISION,
            ActionLayer.L2_SOCIAL,
            ActionLayer.L3_PLATFORM,
        ]

    def requires_platform(self) -> bool:
        """只有 PLATFORM 档需要指定具体平台方言。"""
        return self is SimulationMode.PLATFORM

    @classmethod
    def from_string(cls, name: str) -> "SimulationMode":
        for mode in cls:
            if mode.value == name:
                return mode
        raise ValueError(f"unknown simulation mode: {name!r}")
```

- [ ] **Step 4: 运行测试确认通过**

Run: `poetry run pytest test/wanxiang/test_layers.py -v`
Expected: PASS（7 passed）

- [ ] **Step 5: Commit**

```bash
git add wanxiang/actions/layers.py test/wanxiang/test_layers.py
git commit -m "feat(wanxiang): add ActionLayer and SimulationMode with no-skip-layer rule"
```

---

## Task 2: L1 决策响应动作 与 L2 通用社交动作

L1/L2 是平台无关的动作"词表"。每个动作用 `ActionSpec` 描述：名字、所属层、参数名列表、一句话语义。L1 是决策输出（看完材料后输出一个结构化决策）；L2 是社交交互（agent 互相影响）。

**Files:**
- Create: `wanxiang/actions/l1_decision.py`
- Create: `wanxiang/actions/l2_social.py`
- Test: `test/wanxiang/test_l1_decision.py`
- Test: `test/wanxiang/test_l2_social.py`

- [ ] **Step 1: 写 L1 失败测试**

`test/wanxiang/test_l1_decision.py`：

```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
from wanxiang.actions.l1_decision import L1_ACTIONS
from wanxiang.actions.layers import ActionLayer


def test_l1_has_core_decision_actions():
    names = {a.name for a in L1_ACTIONS}
    # spec §5.1 L1：评分/选择/点击概率/态度极性/愿付价格
    assert {"rate", "choose", "click_probability", "sentiment", "willingness_to_pay"} <= names


def test_l1_actions_all_in_l1_layer():
    assert all(a.layer is ActionLayer.L1_DECISION for a in L1_ACTIONS)


def test_l1_rate_has_score_param():
    rate = next(a for a in L1_ACTIONS if a.name == "rate")
    assert "score" in rate.params


def test_l1_choose_has_option_param():
    choose = next(a for a in L1_ACTIONS if a.name == "choose")
    assert "option" in choose.params


def test_l1_action_names_unique():
    names = [a.name for a in L1_ACTIONS]
    assert len(names) == len(set(names))
```

- [ ] **Step 2: 运行确认失败**

Run: `poetry run pytest test/wanxiang/test_l1_decision.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'wanxiang.actions.l1_decision'`

- [ ] **Step 3: 实现 ActionSpec + L1**

`wanxiang/actions/l1_decision.py`：

```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""L1 决策响应动作（平台无关）。

agent 看完场景材料后输出的结构化决策，可直接聚合成群体分布。
对标 Aaru 的"看材料→输出选择/打分"。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from wanxiang.actions.layers import ActionLayer


@dataclass(frozen=True)
class ActionSpec:
    """一个动作的元数据描述（词表项），不含执行逻辑。"""
    name: str
    layer: ActionLayer
    params: tuple[str, ...] = field(default_factory=tuple)
    description: str = ""


L1_ACTIONS: tuple[ActionSpec, ...] = (
    ActionSpec("rate", ActionLayer.L1_DECISION, ("score",),
               "对材料给出 0-10 购买/喜好评分"),
    ActionSpec("choose", ActionLayer.L1_DECISION, ("option",),
               "在多个选项中选择其一"),
    ActionSpec("click_probability", ActionLayer.L1_DECISION, ("probability",),
               "点击/进一步了解的概率 0-1"),
    ActionSpec("sentiment", ActionLayer.L1_DECISION, ("polarity",),
               "对材料的态度极性 -1..1"),
    ActionSpec("willingness_to_pay", ActionLayer.L1_DECISION, ("price",),
               "愿意支付的价格"),
)
```

- [ ] **Step 4: 运行确认 L1 通过**

Run: `poetry run pytest test/wanxiang/test_l1_decision.py -v`
Expected: PASS（5 passed）

- [ ] **Step 5: 写 L2 失败测试**

`test/wanxiang/test_l2_social.py`：

```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
from wanxiang.actions.l2_social import L2_ACTIONS, l2_action_names
from wanxiang.actions.layers import ActionLayer


def test_l2_has_core_social_actions():
    names = l2_action_names()
    # spec §5.1 L2：发布/转发/点赞/反馈(踩)/评论/关注/收藏/私信/屏蔽
    expected = {"publish", "repost", "like", "dislike", "comment",
                "follow", "collect", "direct_message", "block"}
    assert expected <= names


def test_l2_actions_all_in_l2_layer():
    assert all(a.layer is ActionLayer.L2_SOCIAL for a in L2_ACTIONS)


def test_l2_comment_has_content_param():
    comment = next(a for a in L2_ACTIONS if a.name == "comment")
    assert "content" in comment.params


def test_l2_action_names_unique():
    names = [a.name for a in L2_ACTIONS]
    assert len(names) == len(set(names))


def test_l2_action_names_helper_returns_set():
    assert isinstance(l2_action_names(), set)
```

- [ ] **Step 6: 运行确认 L2 失败**

Run: `poetry run pytest test/wanxiang/test_l2_social.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'wanxiang.actions.l2_social'`

- [ ] **Step 7: 实现 L2**

`wanxiang/actions/l2_social.py`：

```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""L2 通用社交动作（跨平台抽象语义，不绑定任何具体平台）。

L3 平台方言把这些抽象动作映射为具体平台的叫法/规则。
"""
from __future__ import annotations

from wanxiang.actions.l1_decision import ActionSpec
from wanxiang.actions.layers import ActionLayer

L2_ACTIONS: tuple[ActionSpec, ...] = (
    ActionSpec("publish", ActionLayer.L2_SOCIAL, ("content",), "发布内容"),
    ActionSpec("repost", ActionLayer.L2_SOCIAL, ("target_id",), "转发扩散"),
    ActionSpec("like", ActionLayer.L2_SOCIAL, ("target_id",), "正向反馈"),
    ActionSpec("dislike", ActionLayer.L2_SOCIAL, ("target_id",), "负向反馈"),
    ActionSpec("comment", ActionLayer.L2_SOCIAL, ("target_id", "content"), "评论"),
    ActionSpec("follow", ActionLayer.L2_SOCIAL, ("target_user",), "关注/建立关系"),
    ActionSpec("collect", ActionLayer.L2_SOCIAL, ("target_id",), "收藏留存"),
    ActionSpec("direct_message", ActionLayer.L2_SOCIAL, ("target_user", "content"),
               "私信"),
    ActionSpec("block", ActionLayer.L2_SOCIAL, ("target_user",), "屏蔽"),
)


def l2_action_names() -> set[str]:
    return {a.name for a in L2_ACTIONS}
```

- [ ] **Step 8: 运行确认 L2 通过**

Run: `poetry run pytest test/wanxiang/test_l2_social.py -v`
Expected: PASS（5 passed）

- [ ] **Step 9: Commit**

```bash
git add wanxiang/actions/l1_decision.py wanxiang/actions/l2_social.py \
        test/wanxiang/test_l1_decision.py test/wanxiang/test_l2_social.py
git commit -m "feat(wanxiang): add L1 decision and L2 social action vocabularies"
```

---

## Task 3: 平台方言（L3）数据类与加载器

实现 spec §5.4：每个平台 = 声明式 YAML。`DialectLoader` 解析 yaml，把 L2 抽象动作解析为该平台的"启用/别名/扩展/关系语义"，并禁用 `disabled_actions`。

**Files:**
- Create: `wanxiang/actions/dialect.py`
- Create: `wanxiang/actions/l3_dialects/xiaohongshu.yaml`
- Test: `test/wanxiang/test_dialect.py`

- [ ] **Step 1: 写小红书方言 yaml（供测试加载）**

`wanxiang/actions/l3_dialects/xiaohongshu.yaml`：

```yaml
# 小红书平台方言（spec §5.4）
name: xiaohongshu
display_name: 小红书
relationship: weak          # 关系语义：weak | none | strong
feed_algorithm: recommend   # 信息流：recommend | following | hotscore
supported_actions:
  publish:  {alias: 发笔记}
  like:     {alias: 点赞}
  collect:  {alias: 收藏, extra: {合集: true}}
  comment:  {alias: 评论, extra: {追评: true}}
  follow:   {alias: 关注}
  repost:   {alias: 转发}
disabled_actions:
  - dislike   # 小红书没有"踩"
```

- [ ] **Step 2: 写失败测试**

`test/wanxiang/test_dialect.py`：

```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import os

import pytest

from wanxiang.actions.dialect import DialectLoader, PlatformDialect

DIALECT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "..", "wanxiang", "actions", "l3_dialects",
)


@pytest.fixture
def loader():
    return DialectLoader(DIALECT_DIR)


def test_load_xiaohongshu_basic_fields(loader):
    d = loader.load("xiaohongshu")
    assert isinstance(d, PlatformDialect)
    assert d.name == "xiaohongshu"
    assert d.display_name == "小红书"
    assert d.relationship == "weak"
    assert d.feed_algorithm == "recommend"


def test_alias_resolution(loader):
    d = loader.load("xiaohongshu")
    assert d.alias_of("publish") == "发笔记"
    assert d.alias_of("collect") == "收藏"


def test_disabled_action_not_supported(loader):
    d = loader.load("xiaohongshu")
    assert d.supports("dislike") is False
    assert d.supports("like") is True


def test_unsupported_action_alias_raises(loader):
    d = loader.load("xiaohongshu")
    with pytest.raises(KeyError):
        d.alias_of("dislike")


def test_extra_metadata_preserved(loader):
    d = loader.load("xiaohongshu")
    assert d.extra_of("collect") == {"合集": True}
    assert d.extra_of("publish") == {}


def test_supported_action_names(loader):
    d = loader.load("xiaohongshu")
    names = d.supported_action_names()
    assert "publish" in names
    assert "dislike" not in names


def test_unknown_action_in_yaml_rejected(loader, tmp_path):
    # 方言里声明了一个 L2 不存在的抽象动作 → 加载时报错
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "name: bad\ndisplay_name: Bad\nrelationship: none\n"
        "feed_algorithm: hotscore\n"
        "supported_actions:\n  nonexistent_action: {alias: x}\n",
        encoding="utf-8",
    )
    bad_loader = DialectLoader(str(tmp_path))
    with pytest.raises(ValueError, match="not a known L2 action"):
        bad_loader.load("bad")


def test_load_missing_dialect_raises(loader):
    with pytest.raises(FileNotFoundError):
        loader.load("nonexistent_platform")
```

- [ ] **Step 3: 运行确认失败**

Run: `poetry run pytest test/wanxiang/test_dialect.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'wanxiang.actions.dialect'`

- [ ] **Step 4: 实现 dialect.py**

`wanxiang/actions/dialect.py`：

```python
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
```

- [ ] **Step 5: 运行确认通过**

Run: `poetry run pytest test/wanxiang/test_dialect.py -v`
Expected: PASS（8 passed）

- [ ] **Step 6: 提交 dialect 内核 + actions/__init__.py**

```bash
git add wanxiang/actions/dialect.py wanxiang/actions/__init__.py \
        wanxiang/actions/l3_dialects/xiaohongshu.yaml \
        test/wanxiang/test_dialect.py
git commit -m "feat(wanxiang): add PlatformDialect and DialectLoader (L3 yaml)"
```

---

## Task 4: 其余四个平台方言（Twitter / Reddit / 抖音 / 微信）

复用 Task 3 的 loader，只新增 yaml + 针对每个平台关键差异的断言。覆盖 spec §5.4 的平台差异矩阵（含微信强关系）。

**Files:**
- Create: `wanxiang/actions/l3_dialects/twitter.yaml`
- Create: `wanxiang/actions/l3_dialects/reddit.yaml`
- Create: `wanxiang/actions/l3_dialects/douyin.yaml`
- Create: `wanxiang/actions/l3_dialects/wechat.yaml`
- Test: `test/wanxiang/test_dialect_all_platforms.py`

- [ ] **Step 1: 写四平台失败测试**

`test/wanxiang/test_dialect_all_platforms.py`：

```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import os

import pytest

from wanxiang.actions.dialect import DialectLoader

DIALECT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "..", "wanxiang", "actions", "l3_dialects",
)


@pytest.fixture
def loader():
    return DialectLoader(DIALECT_DIR)


@pytest.mark.parametrize("platform", ["twitter", "reddit", "douyin", "wechat"])
def test_all_dialects_load(loader, platform):
    d = loader.load(platform)
    assert d.name == platform


def test_reddit_has_dislike_downvote(loader):
    # Reddit 有踩(downvote)，区别于小红书
    d = loader.load("reddit")
    assert d.supports("dislike") is True
    assert d.alias_of("dislike") == "downvote"
    assert d.relationship == "none"  # 社区无关系


def test_twitter_repost_and_weak_relationship(loader):
    d = loader.load("twitter")
    assert d.alias_of("repost") == "repost"
    assert d.relationship == "weak"


def test_wechat_is_strong_relationship(loader):
    # 微信强关系私域（spec §5.4 唯一 strong）
    d = loader.load("wechat")
    assert d.relationship == "strong"
    assert d.feed_algorithm == "following"


def test_douyin_recommend_feed(loader):
    d = loader.load("douyin")
    assert d.feed_algorithm == "recommend"  # 算法推荐为王
    assert d.alias_of("repost") == "分享"
```

- [ ] **Step 2: 运行确认失败**

Run: `poetry run pytest test/wanxiang/test_dialect_all_platforms.py -v`
Expected: FAIL，`FileNotFoundError`（twitter.yaml 等不存在）

- [ ] **Step 3: 写四个平台 yaml**

`wanxiang/actions/l3_dialects/twitter.yaml`：

```yaml
# Twitter 方言（OASIS 参考实现，弱关系广播）
name: twitter
display_name: Twitter
relationship: weak
feed_algorithm: following
supported_actions:
  publish: {alias: tweet}
  repost:  {alias: repost}
  like:    {alias: like}
  comment: {alias: reply}
  follow:  {alias: follow}
  collect: {alias: bookmark}
  block:   {alias: mute}
disabled_actions: []
```

`wanxiang/actions/l3_dialects/reddit.yaml`：

```yaml
# Reddit 方言（OASIS 参考实现，社区无关系，有踩）
name: reddit
display_name: Reddit
relationship: none
feed_algorithm: hotscore
supported_actions:
  publish: {alias: post}
  repost:  {alias: crosspost}
  like:    {alias: upvote}
  dislike: {alias: downvote}
  comment: {alias: comment}
  collect: {alias: save}
disabled_actions: []
```

`wanxiang/actions/l3_dialects/douyin.yaml`：

```yaml
# 抖音方言（弱关系，算法推荐为王）
name: douyin
display_name: 抖音
relationship: weak
feed_algorithm: recommend
supported_actions:
  publish:  {alias: 发视频}
  repost:   {alias: 分享}
  like:     {alias: 点赞}
  comment:  {alias: 评论}
  follow:   {alias: 关注}
  collect:  {alias: 收藏}
disabled_actions:
  - dislike   # 抖音以"不感兴趣"建模，MVP 先禁用
```

`wanxiang/actions/l3_dialects/wechat.yaml`：

```yaml
# 微信方言（强关系私域，仅好友可见；spec §5.4 第二批）
name: wechat
display_name: 微信
relationship: strong
feed_algorithm: following
supported_actions:
  publish:        {alias: 朋友圈, extra: {仅好友可见: true}}
  repost:         {alias: 转发, extra: {仅好友可见: true}}
  like:           {alias: 点赞}
  comment:        {alias: 评论}
  collect:        {alias: 收藏}
  direct_message: {alias: 私信}
disabled_actions: []
```

- [ ] **Step 4: 运行确认通过**

Run: `poetry run pytest test/wanxiang/test_dialect_all_platforms.py -v`
Expected: PASS（9 passed：4 参数化 + 5 具体断言）

- [ ] **Step 5: 全量回归**

Run: `poetry run pytest test/wanxiang/ -v`
Expected: 全部 PASS（layers 7 + l1 5 + l2 5 + dialect 8 + all_platforms 9 = 34 passed）

- [ ] **Step 6: Commit**

```bash
git add wanxiang/actions/l3_dialects/twitter.yaml \
        wanxiang/actions/l3_dialects/reddit.yaml \
        wanxiang/actions/l3_dialects/douyin.yaml \
        wanxiang/actions/l3_dialects/wechat.yaml \
        test/wanxiang/test_dialect_all_platforms.py
git commit -m "feat(wanxiang): add twitter/reddit/douyin/wechat L3 dialects"
```

---

## Task 5: 模式 × 平台一致性校验（封顶 API）

最后给业务层一个统一入口 `resolve_action_space(mode, dialect=None)`：按档位返回可用动作集，并强制 spec §5.2 的规则（PLATFORM 档必须给 dialect；非 PLATFORM 档给了 dialect 报错）。

**Files:**
- Create: `wanxiang/actions/space.py`
- Modify: `wanxiang/actions/__init__.py`（导出 `resolve_action_space`）
- Test: `test/wanxiang/test_action_space.py`

- [ ] **Step 1: 写失败测试**

`test/wanxiang/test_action_space.py`：

```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import os

import pytest

from wanxiang.actions.dialect import DialectLoader
from wanxiang.actions.layers import SimulationMode
from wanxiang.actions.space import resolve_action_space

DIALECT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "..", "wanxiang", "actions", "l3_dialects",
)


@pytest.fixture
def xhs():
    return DialectLoader(DIALECT_DIR).load("xiaohongshu")


def test_decision_only_returns_only_l1():
    space = resolve_action_space(SimulationMode.DECISION_ONLY)
    assert "rate" in space            # L1
    assert "publish" not in space     # 无 L2


def test_social_returns_l1_and_l2():
    space = resolve_action_space(SimulationMode.SOCIAL)
    assert "rate" in space            # L1
    assert "publish" in space         # L2 抽象名
    assert "dislike" in space         # L2 抽象名（未受平台限制）


def test_platform_filters_by_dialect(xhs):
    space = resolve_action_space(SimulationMode.PLATFORM, dialect=xhs)
    assert "rate" in space            # L1 始终在
    assert "publish" in space         # 小红书支持
    assert "dislike" not in space     # 小红书禁用了 dislike


def test_platform_without_dialect_raises():
    with pytest.raises(ValueError, match="requires a platform dialect"):
        resolve_action_space(SimulationMode.PLATFORM)


def test_non_platform_with_dialect_raises(xhs):
    with pytest.raises(ValueError, match="only PLATFORM mode accepts a dialect"):
        resolve_action_space(SimulationMode.SOCIAL, dialect=xhs)
```

- [ ] **Step 2: 运行确认失败**

Run: `poetry run pytest test/wanxiang/test_action_space.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'wanxiang.actions.space'`

- [ ] **Step 3: 实现 space.py**

`wanxiang/actions/space.py`：

```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""按模拟档位解析可用动作空间（spec §5.2 组合规则的封顶 API）。"""
from __future__ import annotations

from wanxiang.actions.dialect import PlatformDialect
from wanxiang.actions.l1_decision import L1_ACTIONS
from wanxiang.actions.l2_social import L2_ACTIONS
from wanxiang.actions.layers import ActionLayer, SimulationMode


def resolve_action_space(
    mode: SimulationMode,
    dialect: PlatformDialect | None = None,
) -> set[str]:
    """返回该档位下可用的动作名集合。

    - DECISION_ONLY: 仅 L1
    - SOCIAL: L1 + 全部 L2 抽象动作
    - PLATFORM: L1 + 被 dialect 支持的 L2 动作（按平台过滤）

    规则（spec §5.2）：PLATFORM 必须给 dialect；其它档不接受 dialect。
    """
    if mode.requires_platform() and dialect is None:
        raise ValueError("PLATFORM mode requires a platform dialect")
    if not mode.requires_platform() and dialect is not None:
        raise ValueError("only PLATFORM mode accepts a dialect")

    layers = mode.active_layers()
    space: set[str] = set()

    if ActionLayer.L1_DECISION in layers:
        space.update(a.name for a in L1_ACTIONS)

    if ActionLayer.L2_SOCIAL in layers:
        if ActionLayer.L3_PLATFORM in layers:
            # PLATFORM：L2 动作按方言过滤
            space.update(dialect.supported_action_names())
        else:
            # SOCIAL：全部 L2 抽象动作
            space.update(a.name for a in L2_ACTIONS)

    return space
```

- [ ] **Step 4: 运行确认通过**

Run: `poetry run pytest test/wanxiang/test_action_space.py -v`
Expected: PASS（5 passed）

- [ ] **Step 5: 导出公共 API**

修改 `wanxiang/actions/__init__.py` 为：

```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
from wanxiang.actions.layers import ActionLayer, SimulationMode
from wanxiang.actions.dialect import PlatformDialect, DialectLoader
from wanxiang.actions.l1_decision import ActionSpec, L1_ACTIONS
from wanxiang.actions.l2_social import L2_ACTIONS, l2_action_names
from wanxiang.actions.space import resolve_action_space

__all__ = [
    "ActionLayer", "SimulationMode", "PlatformDialect", "DialectLoader",
    "ActionSpec", "L1_ACTIONS", "L2_ACTIONS", "l2_action_names",
    "resolve_action_space",
]
```

- [ ] **Step 6: 全量回归 + 导入冒烟**

Run: `poetry run pytest test/wanxiang/ -v`
Expected: 全部 PASS（34 + 5 = 39 passed）

Run: `poetry run python -c "from wanxiang.actions import resolve_action_space, SimulationMode; print(sorted(resolve_action_space(SimulationMode.DECISION_ONLY)))"`
Expected: 打印 `['choose', 'click_probability', 'rate', 'sentiment', 'willingness_to_pay']`

- [ ] **Step 7: Commit**

```bash
git add wanxiang/actions/space.py wanxiang/actions/__init__.py \
        test/wanxiang/test_action_space.py
git commit -m "feat(wanxiang): add resolve_action_space with mode/dialect validation"
```

---

## 完成标准（Definition of Done）

- [ ] `poetry run pytest test/wanxiang/ -v` 全绿（39 passed）
- [ ] `from wanxiang.actions import resolve_action_space, SimulationMode, DialectLoader` 可用
- [ ] 五个平台方言（twitter/reddit/xiaohongshu/douyin/wechat）均可加载
- [ ] 三档组合规则（不可跳层、PLATFORM 必须带方言）被测试覆盖
- [ ] 未触碰 `oasis/` 任何文件（本计划是纯新增的契约层）

## 下一个计划（不在本计划范围）

- **M0-B 引擎抽象重构**：把 OASIS `platform.py`(1642行) 的业务逻辑迁入"dialect 执行体"，`engine/` 抽取 Channel/编排/trace，让本计划的契约层真正驱动模拟。
- 之后：M1 造人+模拟主链（decision_only 跑通）。
