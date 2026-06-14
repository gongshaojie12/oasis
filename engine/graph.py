# ============= Copyright 2026 @ WANXIANG. All Rights Reserved. =============
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
# ===========================================================================
"""engine.graph — AgentGraph 关系图 (spec §3.1).

实际实现为 ``wanxiang.social_graph.graph`` 的 ``FriendGraph`` + 小世界生成器。
保留本模块以承接 spec §3.1 中"engine/graph.py"的命名约定，并标注关系语义
（无向、邻接表、好友双向存储）来源。

未来如接入 OASIS 的 igraph/neo4j AgentGraph 实现，再在此模块封装出统一
``AgentGraph`` 接口；目前 FriendGraph 即可覆盖 wechat 等闭环平台的可见性
过滤需求。
"""
from wanxiang.social_graph.graph import FriendGraph, generate_small_world

# spec §3.1 / §5.4 / 附录 A 都用了 "AgentGraph" 名字 — 给一个别名以方便上层
# 按 spec 名引用。
AgentGraph = FriendGraph

__all__ = ["FriendGraph", "AgentGraph", "generate_small_world"]
