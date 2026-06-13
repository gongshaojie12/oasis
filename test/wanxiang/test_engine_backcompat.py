# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""验证旧导入路径仍可用，且与 engine 是同一个类对象（确认是再导出而非副本）。"""


def test_old_channel_path_is_engine_channel():
    from engine.channel import Channel as EngineChannel
    from oasis.social_platform.channel import Channel as OasisChannel
    assert OasisChannel is EngineChannel


def test_old_clock_path_is_engine_clock():
    from engine.clock import Clock as EngineClock
    from oasis.clock.clock import Clock as OasisClock
    assert OasisClock is EngineClock


def test_oasis_still_imports():
    import oasis
    assert oasis.__version__
