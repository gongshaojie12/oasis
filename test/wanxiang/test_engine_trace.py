# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import json

from engine.trace import build_trace_insert


def test_build_trace_insert_returns_query_and_params():
    sql, params = build_trace_insert(
        user_id=5, current_time="2026-01-01", action_type="create_post",
        action_info={"content": "hi", "post_id": 1})
    assert "INSERT INTO trace" in sql
    assert "user_id, created_at, action, info" in sql
    assert params[0] == 5
    assert params[1] == "2026-01-01"
    assert params[2] == "create_post"
    assert params[3] == json.dumps({"content": "hi", "post_id": 1})


def test_build_trace_insert_params_is_4_tuple():
    sql, params = build_trace_insert(1, "t", "do_nothing", {})
    assert isinstance(params, tuple)
    assert len(params) == 4
    assert params[3] == "{}"
