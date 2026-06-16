# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""P3: Workspace CRUD + member management + invite system."""
from __future__ import annotations

import asyncio
import secrets
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field

from wanxiang.api.auth_user import require_user
from wanxiang.api.i18n import get_request_locale, t
from wanxiang.api.workspaces import (
    Workspace,
    WorkspaceInvite,
    WorkspaceMember,
)

router = APIRouter()


# ---- Authorization helpers ----

def _get_member(request: Request, workspace_id: str, user_id: str):
    return request.app.state.workspace_store.get_member(
        workspace_id, user_id)


def _require_member(request: Request, workspace_id: str, user_id: str,
                     locale: str):
    m = _get_member(request, workspace_id, user_id)
    if not m:
        raise HTTPException(
            403, t("workspace.not_a_member", locale=locale))
    return m


def _require_admin_or_owner(request: Request, workspace_id: str,
                              user_id: str, locale: str):
    m = _require_member(request, workspace_id, user_id, locale)
    if m.role not in ("owner", "admin"):
        raise HTTPException(
            403, t("workspace.requires_admin", locale=locale))
    return m


def _require_owner(request: Request, workspace_id: str, user_id: str,
                    locale: str):
    m = _require_member(request, workspace_id, user_id, locale)
    if m.role != "owner":
        raise HTTPException(
            403, t("workspace.requires_owner", locale=locale))
    return m


# ---- Schemas ----

class CreateWorkspaceReq(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    type: Literal["personal", "team"] = "team"
    slug: str | None = None


class UpdateWorkspaceReq(BaseModel):
    name: str | None = None
    locale: str | None = None


class InviteMemberReq(BaseModel):
    invited_email: EmailStr
    role: Literal["admin", "member"] = "member"
    expires_in_days: int = Field(default=7, ge=1, le=30)


class AcceptInviteReq(BaseModel):
    token: str


# ---- Routes ----

@router.get("/workspaces")
def list_workspaces(request: Request, user=Depends(require_user)):
    """List workspaces the current user is a member of."""
    workspaces = request.app.state.workspace_store.list_for_user(
        user.user_id)
    return {"workspaces": [w.to_dict() for w in workspaces]}


@router.post("/workspaces")
def create_workspace(req: CreateWorkspaceReq, request: Request,
                       user=Depends(require_user)):
    """Create a new workspace; requesting user becomes owner."""
    locale = get_request_locale(request)
    ws_store = request.app.state.workspace_store
    from wanxiang.api.routes.auth import _make_slug
    slug = req.slug or _make_slug(req.name, ws_store)
    if ws_store.get_by_slug(slug):
        raise HTTPException(
            409, t("workspace.slug_taken", locale=locale))
    ws = Workspace(
        workspace_id="auto", slug=slug, name=req.name, type=req.type,
        owner_user_id=user.user_id, locale=user.locale,
    )
    ws = ws_store.create_workspace(ws)
    ws_store.add_member(WorkspaceMember(
        workspace_id=ws.workspace_id, user_id=user.user_id, role="owner"))
    return ws.to_dict()


@router.get("/workspaces/{slug}")
def get_workspace(slug: str, request: Request,
                    user=Depends(require_user)):
    locale = get_request_locale(request)
    ws = request.app.state.workspace_store.get_by_slug(slug)
    if not ws:
        raise HTTPException(
            404, t("workspace.not_found", locale=locale))
    _require_member(request, ws.workspace_id, user.user_id, locale)
    return ws.to_dict()


@router.patch("/workspaces/{slug}")
def update_workspace(slug: str, req: UpdateWorkspaceReq,
                       request: Request, user=Depends(require_user)):
    locale = get_request_locale(request)
    ws = request.app.state.workspace_store.get_by_slug(slug)
    if not ws:
        raise HTTPException(
            404, t("workspace.not_found", locale=locale))
    _require_admin_or_owner(request, ws.workspace_id, user.user_id, locale)
    patch: dict = {}
    if req.name is not None:
        patch["name"] = req.name
    if req.locale is not None:
        patch["locale"] = req.locale
    ws2 = request.app.state.workspace_store.update_workspace(
        ws.workspace_id, **patch)
    return (ws2 or ws).to_dict()


@router.delete("/workspaces/{slug}")
def delete_workspace(slug: str, request: Request,
                       user=Depends(require_user)):
    locale = get_request_locale(request)
    ws = request.app.state.workspace_store.get_by_slug(slug)
    if not ws:
        raise HTTPException(
            404, t("workspace.not_found", locale=locale))
    _require_owner(request, ws.workspace_id, user.user_id, locale)
    if ws.type == "personal":
        raise HTTPException(
            400, t("workspace.cannot_delete_personal", locale=locale))
    request.app.state.workspace_store.delete_workspace(ws.workspace_id)
    return {"ok": True}


@router.get("/workspaces/{slug}/members")
def list_members(slug: str, request: Request,
                   user=Depends(require_user)):
    locale = get_request_locale(request)
    ws = request.app.state.workspace_store.get_by_slug(slug)
    if not ws:
        raise HTTPException(
            404, t("workspace.not_found", locale=locale))
    _require_member(request, ws.workspace_id, user.user_id, locale)
    members = request.app.state.workspace_store.list_members(
        ws.workspace_id)
    us = request.app.state.user_store
    out = []
    for m in members:
        u = us.get(m.user_id)
        if u:
            d = u.to_safe_dict()
            d["role"] = m.role
            d["joined_at"] = m.joined_at.isoformat()
            out.append(d)
    return {"members": out}


@router.delete("/workspaces/{slug}/members/{member_user_id}")
def remove_member(slug: str, member_user_id: str, request: Request,
                    user=Depends(require_user)):
    locale = get_request_locale(request)
    ws = request.app.state.workspace_store.get_by_slug(slug)
    if not ws:
        raise HTTPException(
            404, t("workspace.not_found", locale=locale))
    _require_admin_or_owner(request, ws.workspace_id, user.user_id, locale)
    target = request.app.state.workspace_store.get_member(
        ws.workspace_id, member_user_id)
    if not target:
        raise HTTPException(
            404, t("workspace.member_not_found", locale=locale))
    if target.role == "owner":
        raise HTTPException(
            400, t("workspace.cannot_remove_owner", locale=locale))
    request.app.state.workspace_store.remove_member(
        ws.workspace_id, member_user_id)
    return {"ok": True}


# ---- Invites ----

@router.post("/workspaces/{slug}/invites")
def create_invite(slug: str, req: InviteMemberReq, request: Request,
                    user=Depends(require_user)):
    locale = get_request_locale(request)
    ws = request.app.state.workspace_store.get_by_slug(slug)
    if not ws:
        raise HTTPException(
            404, t("workspace.not_found", locale=locale))
    _require_admin_or_owner(request, ws.workspace_id, user.user_id, locale)
    inv = WorkspaceInvite(
        invite_id="auto", workspace_id=ws.workspace_id,
        invited_email=str(req.invited_email), role=req.role,
        token=secrets.token_urlsafe(24),
        expires_at=(datetime.now(timezone.utc)
                     + timedelta(days=req.expires_in_days)),
        invited_by_user_id=user.user_id,
    )
    inv = request.app.state.workspace_store.create_invite(inv)
    es = getattr(request.app.state, "email_service", None)
    invite_url = f"/invites/{inv.token}"
    accept_label = "Accept" if locale == "en" else "接受邀请"
    intro_label = ("You are invited to join" if locale == "en"
                    else "邀请你加入")
    subject = ("WANXIANG invite" if locale == "en"
                else "万象团队邀请")
    body = (f"<html><body>"
            f"<p>{intro_label} {ws.name}</p>"
            f"<p><a href=\"{invite_url}\">{accept_label}</a></p>"
            f"<p>token: <code>{inv.token}</code></p>"
            f"</body></html>")
    if es is not None:
        coro = es.send(str(req.invited_email), subject, body)
        try:
            asyncio.create_task(coro)
        except RuntimeError:
            # No running event loop (sync TestClient context). Close the
            # coroutine to avoid 'coroutine was never awaited' warnings.
            try:
                coro.close()
            except Exception:
                pass
    return {
        "invite_id": inv.invite_id, "token": inv.token,
        "expires_at": inv.expires_at.isoformat(),
        "invited_email": inv.invited_email, "role": inv.role,
    }


@router.get("/workspaces/{slug}/invites")
def list_invites(slug: str, request: Request,
                   user=Depends(require_user)):
    locale = get_request_locale(request)
    ws = request.app.state.workspace_store.get_by_slug(slug)
    if not ws:
        raise HTTPException(
            404, t("workspace.not_found", locale=locale))
    _require_admin_or_owner(request, ws.workspace_id, user.user_id, locale)
    invites = request.app.state.workspace_store.list_invites(
        ws.workspace_id)
    return {"invites": [{
        "invite_id": i.invite_id,
        "invited_email": i.invited_email,
        "role": i.role,
        "expires_at": i.expires_at.isoformat(),
        "accepted_at": (i.accepted_at.isoformat()
                          if i.accepted_at else None),
    } for i in invites]}


@router.post("/invites/accept")
def accept_invite(req: AcceptInviteReq, request: Request,
                    user=Depends(require_user)):
    """Use invite token to join a workspace."""
    locale = get_request_locale(request)
    ws_store = request.app.state.workspace_store
    inv = ws_store.get_invite_by_token(req.token)
    if not inv:
        raise HTTPException(
            404, t("workspace.invite_invalid_or_expired", locale=locale))
    if inv.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            400, t("workspace.invite_invalid_or_expired", locale=locale))
    if inv.accepted_at:
        raise HTTPException(
            400, t("workspace.invite_already_accepted", locale=locale))
    if user.email and user.email.lower() != inv.invited_email.lower():
        raise HTTPException(
            403, t("workspace.invite_email_mismatch", locale=locale))
    ws_store.add_member(WorkspaceMember(
        workspace_id=inv.workspace_id, user_id=user.user_id,
        role=inv.role))
    ws_store.consume_invite(req.token)
    ws = ws_store.get_workspace(inv.workspace_id)
    return {"ok": True,
            "workspace": ws.to_dict() if ws else None,
            "role": inv.role}
