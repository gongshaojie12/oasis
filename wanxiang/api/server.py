# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""服务启动器：python -m wanxiang.api.server。

读取 WANXIANG_* 环境变量构造 ServerSettings，然后 uvicorn.run。
支持 --print-config 干跑（不启动），用于配置自检。
"""
from __future__ import annotations

import argparse
import sys
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ServerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WANXIANG_",
                                       env_file=".env",
                                       env_file_encoding="utf-8",
                                       extra="ignore")
    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1, le=65535)
    workers: int = Field(default=1, ge=1, le=64)
    log_level: Literal["critical", "error", "warning", "info", "debug",
                       "trace"] = "info"
    # 给业务代码使用的默认 DeepSeek key（可选；未配置则只能用 stub provider）
    deepseek_api_key: str | None = None
    # ---- Stage 1+2: distributed-mode toggles (默认与单机模式完全一致) ----
    # task_queue: "asyncio" → in-process asyncio.create_task；
    #             "celery"  → 通过 Celery 投递到 worker 进程。
    task_queue: Literal["asyncio", "celery"] = "asyncio"
    # event_bus: "memory" → 进程内 InMemoryEventBus；
    #            "redis"  → 跨进程 RedisEventBus（Pub/Sub + LIST history）。
    event_bus: Literal["memory", "redis"] = "memory"
    redis_url: str = "redis://localhost:6379/2"
    celery_broker: str = "redis://localhost:6379/0"
    celery_backend: str = "redis://localhost:6379/1"
    # ---- P1: brand config (exposed via GET /v1/brand; env-overridable) ----
    brand_name_zh: str = "万象 WANXIANG"
    brand_name_en: str = "WANXIANG"
    brand_short: str = "WANXIANG"
    brand_avatar_zh: str = "象"
    brand_avatar_en: str = "W"
    brand_tagline_zh: str = "AI 首席模拟官"
    brand_tagline_en: str = "AI Chief Simulation Officer"
    # ---- P1: JWT auth ----
    jwt_secret: str = "CHANGE-ME-IN-PRODUCTION-32-bytes-min-secret-key"
    jwt_alg: str = "HS256"
    jwt_access_ttl_minutes: int = 15
    jwt_refresh_ttl_days: int = 7


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="wanxiang-server",
        description="WANXIANG API 服务启动器")
    parser.add_argument("--print-config", action="store_true",
                        help="只打印解析后的配置然后退出")
    args = parser.parse_args(argv)

    settings = ServerSettings()
    if args.print_config:
        # 安全打印：脱敏 api key
        view = settings.model_dump()
        if view.get("deepseek_api_key"):
            view["deepseek_api_key"] = "***"
        print(view)
        return 0

    # 实跑 —— 导入放在这里避免 --print-config 时也启动 uvicorn 网络栈
    import uvicorn
    from wanxiang.api.app import create_app

    uvicorn.run(
        create_app(),
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
        workers=settings.workers if settings.workers > 1 else None,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
