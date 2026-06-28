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

import asyncio
import uuid
from typing import Literal

from fastapi import (APIRouter, Depends, File, HTTPException, Query, Request,
                     UploadFile)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from wanxiang.api.auth_user import require_user
from wanxiang.api.deps import get_model_factory
from wanxiang.api.i18n import get_request_locale, t
from wanxiang.api.sandboxes import ChatMessage, Sandbox, SandboxGroup

router = APIRouter()

# 后台流式模拟任务的强引用集合 —— asyncio.create_task 返回的 task 若无强引用
# 可能被 GC 提前回收，这里持有引用，完成后自动丢弃。
_BG_TASKS: set[asyncio.Task] = set()


def _spawn_bg(coro) -> asyncio.Task:
    task = asyncio.create_task(coro)
    _BG_TASKS.add(task)
    task.add_done_callback(_BG_TASKS.discard)
    return task


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
    distribution_path: str = "cn_national_joint_2020"
    population_size: int = Field(default=1000, ge=10, le=1_000_000)


class UpdateSandboxReq(BaseModel):
    name: str | None = None
    emoji: str | None = None
    description: str | None = None
    population_size: int | None = None
    distribution_path: str | None = None
    archived: bool | None = None
    # group_id 支持显式置 null(移出分组)。用 model_fields_set 区分
    # "未提供" 与 "显式设为 null"。
    group_id: str | None = None


class CreateGroupReq(BaseModel):
    name: str = Field(min_length=1, max_length=64)


class RenameGroupReq(BaseModel):
    name: str = Field(min_length=1, max_length=64)


class AddMessageReq(BaseModel):
    role: Literal["user", "assistant", "system"] = "user"
    content: str = Field(min_length=1, max_length=4000)
    kind: Literal["text", "intent_parsed", "simulation_started",
                  "simulation_progress", "simulation_done",
                  "report_card", "error"] = "text"
    metadata: dict = {}


class ChatSimulateReq(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    # None = 不指定,交给工作区默认模型配置(resolve_workspace_model)。
    # 旧默认值 {"provider": "stub"} 会让请求永远带 stub,导致工作区
    # 配置的通义/DeepSeek 等永远不生效(req_model 非 None → 直接返回 stub)。
    model: dict | None = None
    # 上传文档经 LLM 提炼后的素材;随本条聊天拼进 parse_intent 当 material 线索。
    document_context: str | None = Field(default=None, max_length=4000)


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


# ---- groups（预测任务分组）----
# ⚠️ 必须声明在 /{sandbox_id} 动态段之前，否则 "groups" 会被当成 sandbox_id。

@router.get("/workspaces/{slug}/sandboxes/groups")
def list_groups(slug: str, request: Request, user=Depends(require_user)):
    locale = get_request_locale(request)
    ws = _resolve_workspace_and_member(slug, request, user.user_id, locale)
    groups = request.app.state.sandbox_store.list_groups(ws.workspace_id)
    return {"groups": [g.to_dict() for g in groups]}


@router.post("/workspaces/{slug}/sandboxes/groups")
def create_group(slug: str, req: CreateGroupReq, request: Request,
                 user=Depends(require_user)):
    locale = get_request_locale(request)
    ws = _resolve_workspace_and_member(slug, request, user.user_id, locale)
    g = SandboxGroup(group_id="auto", workspace_id=ws.workspace_id,
                     name=req.name, created_by_user_id=user.user_id)
    g = request.app.state.sandbox_store.create_group(g)
    return g.to_dict()


def _resolve_group(group_id: str, workspace_id: str,
                   request: Request, locale: str) -> SandboxGroup:
    g = request.app.state.sandbox_store.get_group(group_id)
    if not g or g.workspace_id != workspace_id:
        raise HTTPException(404, t("sandbox.group_not_found", locale=locale))
    return g


@router.patch("/workspaces/{slug}/sandboxes/groups/{group_id}")
def rename_group(slug: str, group_id: str, req: RenameGroupReq,
                 request: Request, user=Depends(require_user)):
    locale = get_request_locale(request)
    ws = _resolve_workspace_and_member(slug, request, user.user_id, locale)
    _resolve_group(group_id, ws.workspace_id, request, locale)
    g = request.app.state.sandbox_store.rename_group(group_id, req.name)
    return g.to_dict() if g else None


@router.delete("/workspaces/{slug}/sandboxes/groups/{group_id}")
def delete_group(slug: str, group_id: str, request: Request,
                 user=Depends(require_user)):
    locale = get_request_locale(request)
    ws = _resolve_workspace_and_member(slug, request, user.user_id, locale)
    _resolve_group(group_id, ws.workspace_id, request, locale)
    request.app.state.sandbox_store.delete_group(group_id)
    return {"ok": True}


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
    # 一般字段:None 视为未提供而跳过。
    patch = {k: v for k, v in req.model_dump().items() if v is not None}
    # group_id 例外:显式提供(含 null=移出分组)就应用。
    if "group_id" in req.model_fields_set:
        gid = req.group_id
        if gid is not None:
            # 校验分组存在且属于本工作区
            g = request.app.state.sandbox_store.get_group(gid)
            if not g or g.workspace_id != ws.workspace_id:
                raise HTTPException(404, t("sandbox.group_not_found",
                                            locale=locale))
        patch["group_id"] = gid
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


# ---- 文档上传(提炼成模拟素材)----

_MAX_DOC_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post("/workspaces/{slug}/sandboxes/{sandbox_id}/documents")
async def upload_document(slug: str, sandbox_id: str, request: Request,
                          file: UploadFile = File(...),
                          model_factory=Depends(get_model_factory),
                          user=Depends(require_user)):
    """上传产品资料文档/图片 → 解析 + LLM 提炼成素材(material)。"""
    from wanxiang.api.model_resolve import resolve_workspace_model
    from wanxiang.chat import docparse

    locale = get_request_locale(request)
    ws = _resolve_workspace_and_member(slug, request, user.user_id, locale)
    sb = _resolve_sandbox(sandbox_id, ws.workspace_id, request, locale)

    filename = file.filename or "upload"
    kind = docparse.kind_of(filename)
    if kind == "unsupported":
        raise HTTPException(400, t("doc.unsupported", locale=locale))

    data = await file.read()
    if len(data) > _MAX_DOC_BYTES:
        raise HTTPException(400, t("doc.too_large", locale=locale))
    if not data:
        raise HTTPException(400, t("doc.empty", locale=locale))

    model_cfg = resolve_workspace_model(
        None, ws.workspace_id, request.app.state.model_config_store)
    model_call = model_factory(model_cfg)

    try:
        if kind == "image":
            material = await docparse.distill_image_material(
                data, filename, model_call)
        else:
            text = docparse.extract_text(filename, data)
            material = await docparse.distill_material(text, model_call)
    except docparse.DocParseError as e:
        raise HTTPException(400, str(e))
    except Exception as e:  # noqa: BLE001 — 视觉模型不支持等
        raise HTTPException(
            422, t("doc.distill_failed", locale=locale) + f" ({e})")

    _ = sb  # 鉴权用;素材不落库,由前端随下一条聊天带回
    return {"filename": filename, "kind": kind,
            "material": material, "chars": len(material)}


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


# ---- chat → simulate (shared prep) ----

async def _prepare_chat_simulation(slug: str, sandbox_id: str,
                                    req: ChatSimulateReq, request: Request,
                                    model_factory, user, locale: str):
    """共享:解析 ws/member/sandbox、存 user_msg、parse_intent、存 parse_msg、
    组装 sim_req(样本数=沙盒 population_size)。

    返回 dict:
      - 需澄清/非 simulate:{"clarify": True, "user_msg", "parse_msg", "missing"}
      - 可模拟:{"clarify": False, "user_msg", "parse_msg", "sim_req",
                 "model_cfg", "ws", "sb"}
    """
    ws = _resolve_workspace_and_member(slug, request, user.user_id, locale)
    sb = _resolve_sandbox(sandbox_id, ws.workspace_id, request, locale)
    ss = request.app.state.sandbox_store

    user_msg = ss.add_message(ChatMessage(
        message_id="auto", sandbox_id=sandbox_id, role="user",
        content=req.text, user_id=user.user_id,
    ))

    # Parse intent —— 用工作区默认模型(请求未带 model 时)
    from wanxiang.api.schemas import ModelConfig
    from wanxiang.api.model_resolve import resolve_workspace_model
    from wanxiang.chat.intent import parse_intent
    req_model = None
    if req.model:
        try:
            req_model = ModelConfig(**req.model)
        except Exception:
            req_model = None
    model_cfg = resolve_workspace_model(
        req_model, ws.workspace_id, request.app.state.model_config_store)
    model_call = model_factory(model_cfg)
    # 上传文档已提炼的素材拼进意图解析文本(资料已被提炼得短,不超限)。
    parse_text = req.text
    if req.document_context:
        parse_text = f"{req.text}\n\n【附带资料】\n{req.document_context}"
    intent = await parse_intent(
        parse_text, model_call=model_call,
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
        return {"clarify": True, "user_msg": user_msg,
                "parse_msg": parse_msg, "missing": intent.missing}

    # Override defaults with sandbox config
    sim_req = intent.request
    sim_req.model = model_cfg
    if not sim_req.distribution_path:
        sim_req.distribution_path = sb.distribution_path
    # 人群规模：用户在本句话里明说了人数(n_explicit)→ 以它为准，并把任务
    # population_size 同步更新(让面板/列表显示一致)；没明说 → 沿用任务现值。
    if intent.n_explicit and sim_req.n and sim_req.n != sb.population_size:
        ss.update_sandbox(sandbox_id, population_size=sim_req.n)
        sb = _resolve_sandbox(sandbox_id, ws.workspace_id, request, locale)
    else:
        sim_req.n = sb.population_size

    return {"clarify": False, "user_msg": user_msg, "parse_msg": parse_msg,
            "sim_req": sim_req, "model_cfg": model_cfg, "ws": ws, "sb": sb}


def _record_usage_and_bill(request: Request, ws, sim_req, result) -> None:
    """计费 + 余额扣减(best-effort,绝不影响主流程)。"""
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


def _build_report_card(ss, sandbox_id: str, result) -> ChatMessage:
    report_md = result.markdown or ""
    report = result.report or {}
    rec = report.get("recommendation") or {}
    band = rec.get("confidence_band") or (None, None)
    rng = rec.get("range") or (None, None)
    # 丰富版 metadata:数值统计 + 直方图 + choose 份额,供前端面板渲染。
    return ss.add_message(ChatMessage(
        message_id="auto", sandbox_id=sandbox_id, role="assistant",
        content=report_md, kind="report_card",
        metadata={
            "decision_kind": result.decision_kind,
            "n_valid": result.n_valid,
            "n_total": result.n_total,
            "error_rate": report.get("error_rate"),
            "mean": rec.get("mean"),
            "median": rec.get("median"),
            "p25": band[0],
            "p75": band[1],
            "min": rng[0],
            "max": rng[1],
            "histogram": rec.get("histogram"),
            "top_choice": rec.get("top"),
            "top_share": rec.get("share"),
            "breakdown": report.get("breakdown"),
        },
    ))


# ---- chat → simulate (one-shot, synchronous; kept for backward-compat) ----

@router.post("/workspaces/{slug}/sandboxes/{sandbox_id}/chat")
async def chat_simulate(slug: str, sandbox_id: str, req: ChatSimulateReq,
                         request: Request,
                         model_factory=Depends(get_model_factory),
                         user=Depends(require_user)):
    """User NL message → parse intent → run sim → persist messages → return."""
    locale = get_request_locale(request)
    ss = request.app.state.sandbox_store
    prep = await _prepare_chat_simulation(
        slug, sandbox_id, req, request, model_factory, user, locale)
    user_msg = prep["user_msg"]
    parse_msg = prep["parse_msg"]

    if prep["clarify"]:
        return {
            "user_message": user_msg.to_dict(),
            "assistant_messages": [parse_msg.to_dict()],
            "needs_clarification": True,
            "missing": prep["missing"],
        }

    sim_req = prep["sim_req"]
    ws = prep["ws"]
    from wanxiang.api.routes.simulate import run_simulation_pipeline
    moderator = getattr(request.app.state, "moderator", None)
    dist_store = getattr(request.app.state, "distribution_store", None)
    try:
        result = await run_simulation_pipeline(
            sim_req, model_factory, moderator=moderator, locale=locale,
            distribution_store=dist_store)
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

    _record_usage_and_bill(request, ws, sim_req, result)
    report_msg = _build_report_card(ss, sandbox_id, result)
    return {
        "user_message": user_msg.to_dict(),
        "assistant_messages": [parse_msg.to_dict(), report_msg.to_dict()],
        "report": result.model_dump(),
    }


# ---- chat → simulate (streaming with live progress over SSE) ----

def _build_feed_item(persona, result) -> dict:
    """从 persona + 单条 DecisionResult 抽决策动态 feed 项(JSON 安全)。

    后端只挑字段、不做措辞/本地化(交前端 phraseFeed),保持 locale 无关。
    demographic 是中文键(城市/性别/年龄段),.get 兜底防 KeyError。
    error 非空时 value=None —— 字段照样带,保持 JSON 形状稳定。
    """
    demo = getattr(persona, "demographic", None) or {}
    kind = getattr(result, "kind", None)
    return {
        "agent_id": getattr(persona, "agent_id", None),
        "name": getattr(persona, "name", None),
        "city": demo.get("城市"),
        "gender": demo.get("性别"),
        "age": demo.get("年龄段"),
        "kind": kind.value if hasattr(kind, "value") else str(kind),
        "value": result.value,
        "error": result.error,
    }


async def _run_chat_sim_streaming(*, app_state, run_id: str, sandbox_id: str,
                                   sim_req, model_factory, ws,
                                   locale: str) -> None:
    """后台协程:跑模拟并把进度/结果 publish 到 event_bus[run_id]。

    在 API 进程内由 asyncio.create_task 驱动。event_bus 为 redis 时跨进程
    安全;in-memory 时要求 SSE 订阅与本任务在同一进程(默认单 worker,OK)。
    """
    bus = app_state.event_bus
    ss = app_state.sandbox_store
    from wanxiang.api.routes.simulate import run_simulation_pipeline
    from wanxiang.simulation.aggregate import aggregate
    from wanxiang.simulation.scenario import DecisionKind

    bus.publish(run_id, "started",
                {"run_id": run_id, "n": sim_req.n,
                 "kind": sim_req.scenario.kind})

    # 进度回调:每完成一个 agent 把 done/total + 运行态均值 + 单体决策 feed 推出去。
    # 注意:progress_cb 在事件循环线程内被同步调用(模拟全程 asyncio),
    # 故可直接 publish(InMemory 是同步 put,Redis 是同步 redis-py)。
    def progress_cb(done: int, total: int, partial, persona, result) -> None:
        mean = None
        try:
            agg = aggregate(partial)
            if agg.kind in {DecisionKind.RATE, DecisionKind.CLICK_PROBABILITY,
                            DecisionKind.SENTIMENT, DecisionKind.WTP}:
                mean = agg.stats.get("mean")
        except Exception:  # noqa: BLE001
            mean = None
        bus.publish(run_id, "progress",
                    {"run_id": run_id, "done": done, "total": total,
                     "mean": mean, "kind": sim_req.scenario.kind,
                     "feed": _build_feed_item(persona, result)})

    moderator = getattr(app_state, "moderator", None)
    dist_store = getattr(app_state, "distribution_store", None)
    try:
        result = await run_simulation_pipeline(
            sim_req, model_factory, moderator=moderator, locale=locale,
            progress_cb=progress_cb, distribution_store=dist_store)
    except Exception as e:  # noqa: BLE001
        detail = getattr(e, "detail", None) or str(e)
        try:
            ss.add_message(ChatMessage(
                message_id="auto", sandbox_id=sandbox_id, role="assistant",
                content=str(detail), kind="error",
            ))
        except Exception:
            pass
        bus.publish(run_id, "error", {"run_id": run_id, "error": str(detail)})
        bus.close(run_id)
        return

    _record_usage_and_bill_safe(app_state, ws, sim_req, result)
    report_msg = _build_report_card(ss, sandbox_id, result)
    bus.publish(run_id, "done",
                {"run_id": run_id,
                 "report_card": report_msg.to_dict(),
                 "n_valid": result.n_valid, "n_total": result.n_total})
    bus.close(run_id)


def _record_usage_and_bill_safe(app_state, ws, sim_req, result) -> None:
    """同 _record_usage_and_bill,但用 app_state(后台任务无 request)。"""
    try:
        from wanxiang.api.billing import deduct_workspace
        from wanxiang.api.usage import build_usage_event
        ue = build_usage_event(tenant_id=ws.workspace_id, request=sim_req,
                                 response_kind=result.decision_kind,
                                 status="done")
        app_state.usage_store.record(ue)
        try:
            deduct_workspace(
                workspace_store=app_state.workspace_store,
                transaction_store=app_state.transaction_store,
                workspace_id=ws.workspace_id, amount=ue.cost_units,
                note=f"chat sim n={sim_req.n}", enforce=False)
        except Exception:
            pass
    except Exception:
        pass


@router.post("/workspaces/{slug}/sandboxes/{sandbox_id}/chat/stream")
async def chat_simulate_stream(slug: str, sandbox_id: str,
                                req: ChatSimulateReq, request: Request,
                                model_factory=Depends(get_model_factory),
                                user=Depends(require_user)):
    """解析意图(同步)→ 若需模拟则后台异步跑 + 立即返回 run_id 供 SSE 订阅。"""
    locale = get_request_locale(request)
    prep = await _prepare_chat_simulation(
        slug, sandbox_id, req, request, model_factory, user, locale)
    user_msg = prep["user_msg"]
    parse_msg = prep["parse_msg"]

    if prep["clarify"]:
        return {
            "user_message": user_msg.to_dict(),
            "assistant_messages": [parse_msg.to_dict()],
            "needs_clarification": True,
            "missing": prep["missing"],
            "streaming": False,
        }

    run_id = uuid.uuid4().hex
    _spawn_bg(_run_chat_sim_streaming(
        app_state=request.app.state, run_id=run_id, sandbox_id=sandbox_id,
        sim_req=prep["sim_req"], model_factory=model_factory,
        ws=prep["ws"], locale=locale))

    return {
        "user_message": user_msg.to_dict(),
        "assistant_messages": [parse_msg.to_dict()],
        "streaming": True,
        "run_id": run_id,
        "n": prep["sim_req"].n,
        "kind": prep["sim_req"].scenario.kind,
    }


@router.get("/workspaces/{slug}/sandboxes/{sandbox_id}/runs/{run_id}/events")
async def chat_run_events(slug: str, sandbox_id: str, run_id: str,
                           request: Request,
                           user=Depends(require_user)):
    """SSE:订阅某次流式模拟的进度。鉴权 = 工作区成员 + sandbox 归属校验。"""
    locale = get_request_locale(request)
    ws = _resolve_workspace_and_member(slug, request, user.user_id, locale)
    _resolve_sandbox(sandbox_id, ws.workspace_id, request, locale)
    bus = request.app.state.event_bus

    async def generator():
        async for ev in bus.subscribe(run_id):
            if await request.is_disconnected():
                break
            yield ev.to_sse()

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
