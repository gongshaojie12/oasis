# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import asyncio

import pytest

from engine.channel import Channel, AsyncSafeDict


def test_channel_roundtrip():
    async def scenario():
        ch = Channel()
        mid = await ch.write_to_receive_queue(("agent", "payload", "create_post"))
        got_id, info = await ch.receive_from()
        assert got_id == mid
        assert info == ("agent", "payload", "create_post")
        await ch.send_to((mid, 1, {"success": True}))
        result = await ch.read_from_send_queue(mid)
        assert result == (mid, 1, {"success": True})

    asyncio.run(scenario())


def test_async_safe_dict_basic():
    async def scenario():
        d = AsyncSafeDict()
        await d.put("k", 1)
        assert await d.get("k") == 1
        assert await d.keys() == ["k"]
        assert await d.pop("k") == 1
        assert await d.get("k") is None

    asyncio.run(scenario())
