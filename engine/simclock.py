# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""模拟当前时间计算（平台无关）。

抽取自 OASIS platform.py 中重复 21 次的 current_time 计算块：
- reddit 平台：用沙盒时钟把真实流逝时间放大后叠加到 start_time（连续时间）
- 其它平台：用离散 time_step 字符串

调用方传入 recsys_type（字符串或带 .value 的枚举）即可，无需各自内联。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any


def _recsys_value(recsys_type: Any) -> str:
    """兼容传入字符串或带 .value 的枚举对象。"""
    return getattr(recsys_type, "value", recsys_type)


def compute_current_time(
    recsys_type: Any,
    sandbox_clock: Any,
    start_time: datetime,
    now: datetime | None = None,
) -> Any:
    """返回该平台当前的"时间"表示。

    reddit -> datetime（连续放大时间）；其它 -> str（离散 time_step）。
    `now` 仅在 reddit 分支使用；默认取 datetime.now()，便于测试注入。
    """
    if _recsys_value(recsys_type) == "reddit":
        if now is None:
            now = datetime.now()
        return sandbox_clock.time_transfer(now, start_time)
    return sandbox_clock.get_time_step()
