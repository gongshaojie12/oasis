# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""工作区级模型解析:请求 model > 工作区配置 > stub。

替代断掉的 tenant.default_model_config 链(auth.py 写死 None),
直接按 workspace_id 从 model_config_store 读取。
"""
from __future__ import annotations


def resolve_workspace_model(req_model, workspace_id, store):
    """返回一个非空 ModelConfig。

    - req_model 非空 → 直接用(请求 wins)。
    - 否则 store 有该 workspace 配置 → 组装 ModelConfig。
    - 否则 → ModelConfig(provider="stub")。
    """
    from wanxiang.api.schemas import ModelConfig
    if req_model is not None:
        return req_model
    rec = store.get(workspace_id) if (store and workspace_id) else None
    if rec is not None:
        return ModelConfig(
            provider=rec.provider,
            api_key=rec.api_key,
            base_url=rec.base_url,
            model_name=rec.model_name,
        )
    return ModelConfig(provider="stub")
