# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""P6: Workspace-scoped Sandbox CRUD + Chat message routes.

Endpoints (all under /v1):
- GET    /workspaces/{slug}/sandboxes
- POST   /workspaces/{slug}/sandboxes
- GET    /workspaces/{slug}/sandboxes/{sandbox_id}
- PATCH  /workspaces/{slug}/sandboxes/{sandbox_id}
- DELETE /workspaces/{slug}/sandboxes/{sandbox_id}
- GET    /workspaces/{slug}/sandboxes/{sandbox_id}/messages
- POST   /workspaces/{slug}/sandboxes/{sandbox_id}/messages
- POST   /workspaces/{slug}/sandboxes/{sandbox_id}/chat
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from wanxiang.api.auth_user import require_user
from wanxiang.api.deps import get_model_factory
from wanxiang.api.i18n import get_request_locale, t
from wanxiang.api.sandboxes import ChatMessage, Sandbox

router = APIRouter()


# ---- helpers ----

def _resolve_workspace_and_member(slug: str, request: Request,
                                    user_id: str, locale: str):
    from wanxiang.api.routes.workspaces import _require_member
    ws = request.app.state.workspace_store.get_by_slug(slug)
    if not ws:
        raise HTTPException(404, t("workspace.not_found", locale=locale))
    _require_member(request, ws.workspace_id, user_id, locale)
    return ws


def _resolve_sandbox(sandbox_id: str, workspace_id: str,
                      request: Request, locale: str) -> Sandbox:
    sb = request.app.state.sandbox_store.get_sandbox(sandbox_id)
    if not sb:
        raise HTTPException(404, t("sandbox.not_found", locale=locale))
    if sb.workspace_id != workspace_id:
        raise HTTPException(403, t("sandbox.wrong_workspace",
                                     locale=locale))
    return sb


# ---- schemas ----

class CreateSandboxReq(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    emoji: str = Field(default="🥤", max_length=8)
    description: str = ""
    distribution_path: str = (
        "wanxiang/datasources/distributions/cn_z_generation_v1.yaml")
    population_size: int = Field(default=1000, ge=10, le=1_000_000)


class UpdateSandboxReq(BaseModel):
    name: str | None = None
    emoji: str | None = None
    description: str | None = None
    population_size: int | None = None
    distribution_path: str | None = None
    archived: bool | None = None


class AddMessageReq(BaseModel):
    role: Literal["user", "assistant", "system"] = "user"
    content: str = Field(min_length=1, max_length=4000)
    kind: Literal["text", "intent_parsed", "simulation_started",
                  "simulation_progress", "simulation_done",
                  "report_card", "error"] = "text"
    metadata: dict = {}


class ChatSimulateReq(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    model: dict = {"provider": "stub"}


# ---- CRUD ----

@router.get("/workspaces/{slug}/sandboxes")
def list_sandboxes(slug: str, request: Request,
                    user=Depends(require_user),
                    include_archived: bool = False):
    locale = get_request_locale(request)
    ws = _resolve_workspace_and_member(slug, request, user.user_id, locale)
    sandboxes = request.app.state.sandbox_store.list_for_workspace(
        ws.workspace_id, include_archived=include_archived)
    return {"sandboxes": [s.to_dict() for s in sandboxes]}


@router.post("/workspaces/{slug}/sandboxes")
def create_sandbox(slug: str, req: CreateSandboxReq, request: Request,
                    user=Depends(require_user)):
    locale = get_request_locale(request)
    ws = _resolve_workspace_and_member(slug, request, user.user_id, locale)
    sb = Sandbox(
        sandbox_id="auto", workspace_id=ws.workspace_id,
        name=req.name, emoji=req.emoji, description=req.description,
        distribution_path=req.distribution_path,
        population_size=req.population_size,
        created_by_user_id=user.user_id,
    )
    sb = request.app.state.sandbox_store.create_sandbox(sb)
    return sb.to_dict()


@router.get("/workspaces/{slug}/sandboxes/{sandbox_id}")
def get_sandbox(slug: str, sandbox_id: str, request: Request,
                 user=Depends(require_user)):
    locale = get_request_locale(request)
    ws = _resolve_workspace_and_member(slug, request, user.user_id, locale)
    sb = _resolve_sandbox(sandbox_id, ws.workspace_id, request, locale)
    return sb.to_dict()


@router.patch("/workspaces/{slug}/sandboxes/{sandbox_id}")
def update_sandbox(slug: str, sandbox_id: str, req: UpdateSandboxReq,
                    request: Request, user=Depends(require_user)):
    locale = get_request_locale(request)
    ws = _resolve_workspace_and_member(slug, request, user.user_id, locale)
    _resolve_sandbox(sandbox_id, ws.workspace_id, request, locale)
    patch = {k: v for k, v in req.model_dump().items() if v is not None}
    sb = request.app.state.sandbox_store.update_sandbox(sandbox_id, **patch)
    return sb.to_dict() if sb else None


@router.delete("/workspaces/{slug}/sandboxes/{sandbox_id}")
def delete_sandbox(slug: str, sandbox_id: str, request: Request,
                    user=Depends(require_user)):
    locale = get_request_locale(request)
    ws = _resolve_workspace_and_member(slug, request, user.user_id, locale)
    _resolve_sandbox(sandbox_id, ws.workspace_id, request, locale)
    request.app.state.sandbox_store.delete_sandbox(sandbox_id)
    return {"ok": True}


# ---- messages ----

@router.get("/workspaces/{slug}/sandboxes/{sandbox_id}/messages")
def list_messages(slug: str, sandbox_id: str, request: Request,
                   user=Depends(require_user),
                   limit: int = Query(200, ge=1, le=1000),
                   after: str | None = None):
    locale = get_request_locale(request)
    ws = _resolve_workspace_and_member(slug, request, user.user_id, locale)
    _resolve_sandbox(sandbox_id, ws.workspace_id, request, locale)
    msgs = request.app.state.sandbox_store.list_messages(
        sandbox_id, limit=limit, after_message_id=after)
    return {"messages": [m.to_dict() for m in msgs]}


@router.post("/workspaces/{slug}/sandboxes/{sandbox_id}/messages")
def add_message(slug: str, sandbox_id: str, req: AddMessageReq,
                 request: Request, user=Depends(require_user)):
    locale = get_request_locale(request)
    ws = _resolve_workspace_and_member(slug, request, user.user_id, locale)
    _resolve_sandbox(sandbox_id, ws.workspace_id, request, locale)
    msg = ChatMessage(
        message_id="auto", sandbox_id=sandbox_id,
        role=req.role, content=req.content, kind=req.kind,
        metadata=req.metadata,
        user_id=user.user_id if req.role == "user" else None,
    )
    msg = request.app.state.sandbox_store.add_message(msg)
    return msg.to_dict()


# ---- chat → simulate (one-shot) ----

@router.post("/workspaces/{slug}/sandboxes/{sandbox_id}/chat")
async def chat_simulate(slug: str, sandbox_id: str, req: ChatSimulateReq,
                         request: Request,
                         model_factory=Depends(get_model_factory),
                         user=Depends(require_user)):
    """User NL message → parse intent → run sim → persist messages → return."""
    locale = get_request_locale(request)
    ws = _resolve_workspace_and_member(slug, request, user.user_id, locale)
    sb = _resolve_sandbox(sandbox_id, ws.workspace_id, request, locale)
    ss = request.app.state.sandbox_store

    user_msg = ss.add_message(ChatMessage(
        message_id="auto", sandbox_id=sandbox_id, role="user",
        content=req.text, user_id=user.user_id,
    ))

    # Parse intent (stub provider unless caller overrides)
    from wanxiang.api.schemas import ModelConfig
    from wanxiang.chat.intent import parse_intent
    try:
        model_cfg = ModelConfig(**(req.model or {"provider": "stub"}))
    except Exception:
        model_cfg = ModelConfig(provider="stub")
    model_call = model_factory(model_cfg)
    intent = await parse_intent(
        req.text, model_call=model_call,
        default_distribution_path=sb.distribution_path,
        locale=locale,
    )
    parse_msg = ss.add_message(ChatMessage(
        message_id="auto", sandbox_id=sandbox_id, role="assistant",
        content=intent.explanation or "...",
        kind="intent_parsed",
        metadata={"intent": intent.intent,
                  "missing": intent.missing,
                  "confidence": intent.confidence},
    ))
    if intent.intent != "simulate" or intent.request is None:
        return {
            "user_message": user_msg.to_dict(),
            "assistant_messages": [parse_msg.to_dict()],
            "needs_clarification": True,
            "missing": intent.missing,
        }

    # Override defaults with sandbox config when blank
    sim_req = intent.request
    if not sim_req.distribution_path:
        sim_req.distribution_path = sb.distribution_path
    if not sim_req.n:
        sim_req.n = min(sb.population_size, 50)

    from wanxiang.api.routes.simulate import run_simulation_pipeline
    moderator = getattr(request.app.state, "moderator", None)
    try:
        result = await run_simulation_pipeline(
            sim_req, model_factory, moderator=moderator, locale=locale)
    except HTTPException as e:
        err_msg = ss.add_message(ChatMessage(
            message_id="auto", sandbox_id=sandbox_id, role="assistant",
            content=str(e.detail), kind="error",
        ))
        return {"user_message": user_msg.to_dict(),
                "assistant_messages": [parse_msg.to_dict(),
                                        err_msg.to_dict()],
                "error": str(e.detail)}
    except Exception as e:  # noqa: BLE001
        err_msg = ss.add_message(ChatMessage(
            message_id="auto", sandbox_id=sandbox_id, role="assistant",
            content=str(e), kind="error",
        ))
        return {"user_message": user_msg.to_dict(),
                "assistant_messages": [parse_msg.to_dict(),
                                        err_msg.to_dict()],
                "error": str(e)}

    # Record usage + deduct balance (best-effort, never fail the response)
    try:
        from wanxiang.api.billing import deduct_workspace
        from wanxiang.api.usage import build_usage_event
        ue = build_usage_event(tenant_id=ws.workspace_id, request=sim_req,
                                 response_kind=result.decision_kind,
                                 status="done")
        request.app.state.usage_store.record(ue)
        try:
            deduct_workspace(
                workspace_store=request.app.state.workspace_store,
                transaction_store=request.app.state.transaction_store,
                workspace_id=ws.workspace_id, amount=ue.cost_units,
                note=f"chat sim n={sim_req.n}", enforce=False)
        except Exception:
            pass
    except Exception:
        pass

    report_md = result.markdown or ""
    rec = (result.report or {}).get("recommendation") or {}
    report_msg = ss.add_message(ChatMessage(
        message_id="auto", sandbox_id=sandbox_id, role="assistant",
        content=report_md, kind="report_card",
        metadata={
            "decision_kind": result.decision_kind,
            "n_valid": result.n_valid,
            "n_total": result.n_total,
            "mean": rec.get("mean"),
            "top_choice": rec.get("top_choice"),
        },
    ))
    return {
        "user_message": user_msg.to_dict(),
        "assistant_messages": [parse_msg.to_dict(), report_msg.to_dict()],
        "report": result.model_dump(),
    }
