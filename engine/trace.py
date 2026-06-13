# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""trace 行为日志写入构建（平台无关）。

抽取自 OASIS PlatformUtils._record_trace 的 SQL 构建部分。时间计算
（依赖 recsys_type / clock）仍由调用方完成；本函数只负责把字段组装成
可执行的 INSERT 语句与参数。
"""
from __future__ import annotations

import json
from typing import Any


def build_trace_insert(
    user_id: Any,
    current_time: Any,
    action_type: str,
    action_info: Any,
) -> tuple[str, tuple]:
    """返回 (sql, params)，用于向 trace 表插入一条行为日志。

    action_info 会被 json.dumps 序列化为字符串存入 info 列。
    """
    sql = ("INSERT INTO trace (user_id, created_at, action, info) "
           "VALUES (?, ?, ?, ?)")
    params = (user_id, current_time, action_type, json.dumps(action_info))
    return sql, params
