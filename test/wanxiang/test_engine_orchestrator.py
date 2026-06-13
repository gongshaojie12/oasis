# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import asyncio

import pytest

from engine.orchestrator import dispatch_action


class FakeOwner:
    """模拟 Platform：含不同参数个数的异步动作方法。"""

    async def refresh(self, agent_id):           # 2 params (self, agent_id)
        return {"ok": "refresh", "agent": agent_id}

    async def create_post(self, agent_id, content):  # 3 params
        return {"ok": "post", "agent": agent_id, "content": content}

    async def update_rec_table(self):            # 1 param (self only)
        return {"ok": "rec"}


def test_dispatch_two_param_action_passes_agent_id():
    owner = FakeOwner()
    r = asyncio.run(dispatch_action(owner, "refresh", agent_id=7, message=None))
    assert r == {"ok": "refresh", "agent": 7}


def test_dispatch_three_param_action_passes_message_as_second():
    owner = FakeOwner()
    r = asyncio.run(
        dispatch_action(owner, "create_post", agent_id=3, message="hello"))
    assert r == {"ok": "post", "agent": 3, "content": "hello"}


def test_dispatch_one_param_action_ignores_agent_and_message():
    owner = FakeOwner()
    r = asyncio.run(
        dispatch_action(owner, "update_rec_table", agent_id=99, message="x"))
    assert r == {"ok": "rec"}


def test_dispatch_unknown_action_raises():
    owner = FakeOwner()
    with pytest.raises(ValueError, match="not supported"):
        asyncio.run(dispatch_action(owner, "nonexistent", agent_id=1, message=None))


def test_dispatch_rejects_too_many_params():
    class Bad:
        async def weird(self, agent_id, message, extra):  # 4 params
            return None
    with pytest.raises(ValueError, match="parameters are not"):
        asyncio.run(dispatch_action(Bad(), "weird", agent_id=1, message="m"))
