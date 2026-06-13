# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""验证 OASIS 重接 engine 机制后仍正常工作。"""
import asyncio
import sqlite3
from datetime import datetime


def test_oasis_imports_after_rewire():
    import oasis
    assert oasis.__version__


def test_record_trace_writes_row(tmp_path):
    from oasis.social_platform.platform_utils import PlatformUtils
    from oasis.social_platform.typing import RecsysType
    from engine.clock import Clock

    db_path = str(tmp_path / "t.db")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("CREATE TABLE trace (user_id INTEGER, created_at TEXT, "
                "action TEXT, info TEXT)")
    conn.commit()

    utils = PlatformUtils(
        db=conn, db_cursor=cur, start_time=datetime.now(),
        sandbox_clock=Clock(k=60), show_score=False,
        recsys_type=RecsysType.TWITTER, report_threshold=1)
    utils._record_trace(1, "create_post", {"content": "hi"})

    cur.execute("SELECT user_id, action, info FROM trace")
    row = cur.fetchone()
    conn.close()
    assert row[0] == 1
    assert row[1] == "create_post"
    assert '"content": "hi"' in row[2]


def test_platform_dispatch_via_orchestrator(tmp_path):
    from oasis.social_platform.platform import Platform
    from oasis.social_platform.typing import ActionType
    from engine.channel import Channel

    db_path = str(tmp_path / "p.db")
    channel = Channel()
    platform = Platform(db_path=db_path, channel=channel,
                        recsys_type="twitter")

    async def scenario():
        task = asyncio.create_task(platform.running())
        mid = await channel.write_to_receive_queue(
            (0, None, ActionType.DO_NOTHING.value))
        resp = await channel.read_from_send_queue(mid)
        await channel.write_to_receive_queue(
            (None, None, ActionType.EXIT.value))
        await task
        return resp

    resp = asyncio.run(scenario())
    assert resp[2]["success"] is True
