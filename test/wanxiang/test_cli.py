# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""CLI 冒烟测试：用 stub 模型走完整链路。"""
import json
import os
import subprocess
import sys

PY = r"D:\software\conda_data\envs\oasis\python.exe"
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", ".."))
DIST = os.path.join(PROJECT_ROOT, "test", "wanxiang", "fixtures",
                    "cn_z_generation_v1.yaml")


def _run(*args):
    cmd = [PY, "-m", "wanxiang.cli", *args]
    return subprocess.run(cmd, capture_output=True, text=True,
                          cwd=PROJECT_ROOT, encoding="utf-8")


def test_cli_help_works():
    res = _run("--help")
    assert res.returncode == 0
    assert "simulate" in res.stdout.lower() or "simulate" in res.stderr.lower()


def test_cli_simulate_rate_with_stub():
    res = _run(
        "simulate",
        "--distribution", DIST,
        "--n", "20", "--seed", "1",
        "--material", "新品 ¥6", "--question", "0-10 评分",
        "--kind", "rate",
        "--rounds", "0",  # decision_only path
        "--model", "stub",
    )
    assert res.returncode == 0, f"stderr={res.stderr}"
    # 应该打印 markdown 报告
    assert "万象模拟报告" in res.stdout
    # 最后一行是结构化 JSON summary
    last_line = [ln for ln in res.stdout.strip().splitlines() if ln.strip()][-1]
    summary = json.loads(last_line)
    assert summary["n_total"] == 20
    assert summary["decision_kind"] == "rate"


def test_cli_simulate_choose_with_stub():
    res = _run(
        "simulate",
        "--distribution", DIST,
        "--n", "10", "--seed", "1",
        "--material", "三口味", "--question", "选一个",
        "--kind", "choose",
        "--options", "青提,白桃,海盐荔枝",
        "--rounds", "0",
        "--model", "stub",
    )
    assert res.returncode == 0, f"stderr={res.stderr}"
    last_line = [ln for ln in res.stdout.strip().splitlines() if ln.strip()][-1]
    summary = json.loads(last_line)
    assert summary["decision_kind"] == "choose"
    assert summary["n_total"] == 10


def test_cli_simulate_choose_requires_options():
    res = _run(
        "simulate",
        "--distribution", DIST,
        "--n", "5", "--seed", "1",
        "--material", "m", "--question", "q",
        "--kind", "choose",
        # 没传 --options
        "--rounds", "0",
        "--model", "stub",
    )
    assert res.returncode != 0
    err = (res.stderr + res.stdout).lower()
    assert "option" in err  # 错误信息提及 options


def test_cli_simulate_with_social_rounds():
    """rounds > 0 也应能跑通（甲方案社交涌现）。"""
    res = _run(
        "simulate",
        "--distribution", DIST,
        "--n", "8", "--seed", "1",
        "--material", "m", "--question", "0-10 评分",
        "--kind", "rate",
        "--rounds", "1",
        "--model", "stub",
    )
    assert res.returncode == 0, f"stderr={res.stderr}"
    assert "万象模拟报告" in res.stdout
