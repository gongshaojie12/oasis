# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""动作分发机制（平台无关）。

抽取自 OASIS Platform.running() 的内联分发逻辑：按动作名在 handler
对象上查找异步方法，按其参数个数（含 self：1/2/3）构建调用。行为与
原内联逻辑逐字等价。
"""
from __future__ import annotations

from typing import Any


async def dispatch_action(
    handler_owner: Any,
    action_name: str,
    agent_id: Any,
    message: Any,
) -> Any:
    """在 handler_owner 上找名为 action_name 的异步方法并调用。

    参数构建规则（与 OASIS 原逻辑一致，参数个数含 self）：
    - 1 个参数 (仅 self): 不传 agent_id / message
    - 2 个参数 (self, agent_id): 传 agent_id
    - 3 个参数 (self, agent_id, <second>): 传 agent_id + 把 message
      作为第二个业务参数（按其形参名传入）
    - >3 个参数: 不支持，抛 ValueError
    """
    action_function = getattr(handler_owner, action_name, None)
    if action_function is None:
        raise ValueError(f"Action {action_name} is not supported")

    func_code = action_function.__code__
    param_names = func_code.co_varnames[:func_code.co_argcount]
    len_param_names = len(param_names)
    if len_param_names > 3:
        raise ValueError(
            f"Functions with {len_param_names} parameters are not "
            f"supported.")

    params: dict[str, Any] = {}
    if len_param_names >= 2:
        params["agent_id"] = agent_id
    if len_param_names == 3:
        second_param_name = param_names[2]
        params[second_param_name] = message

    return await action_function(**params)
