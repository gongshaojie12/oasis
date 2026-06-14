# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""POST /v1/chat/parse —— NL → SimulateRequest（M3-8）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from wanxiang.api.auth import require_tenant
from wanxiang.api.deps import get_model_factory
from wanxiang.api.schemas import ModelConfig
from wanxiang.api.tenancy import TenantInfo
from wanxiang.chat.intent import IntentParseResult, parse_intent

router = APIRouter()


class ChatParseRequest(BaseModel):
    user_text: str
    default_distribution_path: str | None = None


@router.post("/chat/parse", response_model=IntentParseResult)
async def chat_parse(
    body: ChatParseRequest,
    model_factory=Depends(get_model_factory),
    tenant: TenantInfo = Depends(require_tenant),
) -> IntentParseResult:
    # MVP：用 stub provider 跑意图解析；后续可让 tenant 配真实 model
    model_call = model_factory(ModelConfig(provider="stub"))
    return await parse_intent(body.user_text, model_call,
                                default_distribution_path=body.default_distribution_path)
