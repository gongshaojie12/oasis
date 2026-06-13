# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""simulate 子命令：把 wanxiang 全链路串成命令行可执行。

加载分布 → 造人 → (社交多轮) 决策 → 校准（如果给了 truth）→ 报告。
最后一行打印结构化 JSON 摘要，方便机器消费。
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys

from wanxiang.datasources import load_distribution
from wanxiang.models import make_deepseek_call, make_stub_call  # noqa: F401
from wanxiang.personas import PersonaBuilder
from wanxiang.reporting import build_report, render_markdown
from wanxiang.simulation import (BatchRunner, DecisionKind, ScenarioConfig,
                                 SocialRoundsRunner, aggregate)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wanxiang", description="万象 WANXIANG 命令行")
    sub = parser.add_subparsers(dest="command", required=True)

    sim = sub.add_parser("simulate", help="端到端跑一次模拟并打印报告")
    sim.add_argument("--distribution", required=True,
                     help="分布 yaml 文件路径")
    sim.add_argument("--n", type=int, required=True,
                     help="虚拟人数量")
    sim.add_argument("--seed", type=int, default=42,
                     help="抽样确定性种子（默认 42）")
    sim.add_argument("--material", required=True, help="场景材料文本")
    sim.add_argument("--question", required=True, help="场景问题文本")
    sim.add_argument("--kind", required=True,
                     choices=[k.value for k in DecisionKind],
                     help="决策类型")
    sim.add_argument("--options", default=None,
                     help="CHOOSE 时的可选项，逗号分隔")
    sim.add_argument("--rounds", type=int, default=0,
                     help="社交涌现轮数；0 = 纯 decision_only")
    sim.add_argument("--model", default="stub",
                     choices=["stub", "deepseek"],
                     help="模型适配器（stub 不需 API key）")
    sim.add_argument("--api-key", default=None,
                     help="DeepSeek API key（--model deepseek 时必填）")
    sim.add_argument("--concurrency", type=int, default=16,
                     help="LLM 并发上限")
    return parser


def _make_smart_stub(scenario: ScenarioConfig):
    """构造一个会返回合法 JSON 的本地 stub，不依赖外部 LLM 也不需 API key。

    camel 自带的 STUB 永远返回 "Lorem Ipsum"，无法走通 decision 解析。
    本 stub 按 scenario.decision_kind 给出语义正确的 JSON：
    用 system prompt 的 hash 作为确定性熵源，让不同画像得到不同输出，
    从而 aggregate 出来的均值/份额不是常数。
    """
    kind = scenario.decision_kind
    options = tuple(scenario.options or ())

    async def call(messages: list[dict]) -> str:
        sys_content = messages[0]["content"] if messages else ""
        digest = hashlib.md5(sys_content.encode("utf-8")).digest()
        seed = digest[0]
        if kind is DecisionKind.RATE:
            return json.dumps({"score": int(seed % 11)})
        if kind is DecisionKind.CHOOSE:
            choice = options[seed % len(options)] if options else ""
            return json.dumps({"option": choice}, ensure_ascii=False)
        if kind is DecisionKind.CLICK_PROBABILITY:
            return json.dumps({"probability": round((seed % 100) / 100.0, 2)})
        if kind is DecisionKind.SENTIMENT:
            return json.dumps({"polarity": round(((seed % 201) - 100) / 100.0, 2)})
        if kind is DecisionKind.WTP:
            return json.dumps({"price": int(seed % 100)})
        return "{}"

    return call


def _make_model_call(args, scenario: ScenarioConfig):
    if args.model == "stub":
        return _make_smart_stub(scenario)
    if args.model == "deepseek":
        if not args.api_key:
            raise SystemExit("--model deepseek 需要 --api-key")
        return make_deepseek_call(api_key=args.api_key)
    raise SystemExit(f"unknown model: {args.model}")


async def _run_simulation(args, scenario, personas, model_call):
    if args.rounds == 0:
        runner = BatchRunner(decision_concurrency=args.concurrency)
        results = await runner.run_all(personas, scenario, model_call)
    else:
        runner = SocialRoundsRunner(rounds=args.rounds,
                                    decision_concurrency=args.concurrency)
        results, _history = await runner.run(personas, scenario, model_call)
    return results


def _run_simulate(args) -> int:
    kind = DecisionKind(args.kind)
    options = None
    if kind is DecisionKind.CHOOSE:
        if not args.options:
            print("error: --kind choose 需要 --options（逗号分隔）",
                  file=sys.stderr)
            return 2
        options = tuple(s.strip() for s in args.options.split(","))

    scenario = ScenarioConfig(
        material=args.material, question=args.question,
        decision_kind=kind, options=options)

    distribution = load_distribution(args.distribution)
    pb = PersonaBuilder()
    personas = pb.sample(distribution, n=args.n, seed=args.seed)

    model_call = _make_model_call(args, scenario)
    results = asyncio.run(_run_simulation(args, scenario, personas, model_call))
    report = aggregate(results)
    structured = build_report(scenario=scenario, aggregate=report,
                              persona_count=args.n)

    md = render_markdown(structured)
    print(md)

    summary = {
        "decision_kind": kind.value,
        "n_total": report.n_total,
        "n_valid": report.n_valid,
        "error_count": report.error_count,
        "error_rate": report.error_rate,
        "top": report.stats.get("top") if kind is DecisionKind.CHOOSE else None,
        "mean": report.stats.get("mean") if kind is not DecisionKind.CHOOSE else None,
        "rounds": args.rounds,
    }
    print(json.dumps(summary, ensure_ascii=False))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "simulate":
        return _run_simulate(args)
    parser.print_help()
    return 1
