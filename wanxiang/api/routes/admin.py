# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""P4: Super-admin routes for user/workspace/balance management.

All endpoints require ``user.is_super_admin = True``.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from wanxiang.api.auth_user import require_super_admin
from wanxiang.api.billing import refund_workspace, topup_workspace
from wanxiang.api.i18n import get_request_locale, t

router = APIRouter()


# ---- Schemas ----

class TopUpReq(BaseModel):
    workspace_id: str
    amount: int = Field(gt=0, le=10_000_000)
    note: str = ""


class RefundReq(BaseModel):
    workspace_id: str
    amount: int = Field(gt=0, le=10_000_000)
    note: str = ""
    related_task_id: str | None = None


class SetSuperAdminReq(BaseModel):
    user_id: str
    is_super_admin: bool


# ---- Routes ----

@router.get("/admin/users")
def list_users(request: Request,
                 limit: int = Query(100, ge=1, le=1000),
                 user=Depends(require_super_admin)):
    """List all users (paginated). Super-admin only."""
    us = request.app.state.user_store
    users = us.list_all(limit=limit) if hasattr(us, "list_all") else []
    return {"users": [u.to_safe_dict() for u in users]}


@router.get("/admin/workspaces")
def list_all_workspaces(request: Request,
                          limit: int = Query(100, ge=1, le=1000),
                          user=Depends(require_super_admin)):
    ws_store = request.app.state.workspace_store
    workspaces = (ws_store.list_all(limit=limit)
                   if hasattr(ws_store, "list_all") else [])
    return {"workspaces": [w.to_dict() for w in workspaces]}


@router.post("/admin/topup")
def admin_topup(req: TopUpReq, request: Request,
                  user=Depends(require_super_admin)):
    """Manual top-up to a workspace balance."""
    locale = get_request_locale(request)
    try:
        tx = topup_workspace(
            workspace_store=request.app.state.workspace_store,
            transaction_store=request.app.state.transaction_store,
            workspace_id=req.workspace_id,
            amount=req.amount, note=req.note,
            created_by_user_id=user.user_id,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    return tx.to_dict()


@router.post("/admin/refund")
def admin_refund(req: RefundReq, request: Request,
                   user=Depends(require_super_admin)):
    locale = get_request_locale(request)
    try:
        tx = refund_workspace(
            workspace_store=request.app.state.workspace_store,
            transaction_store=request.app.state.transaction_store,
            workspace_id=req.workspace_id,
            amount=req.amount, note=req.note,
            related_task_id=req.related_task_id,
            created_by_user_id=user.user_id,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    return tx.to_dict()


@router.get("/admin/transactions")
def list_transactions(request: Request,
                        workspace_id: str | None = Query(None),
                        kind: str | None = Query(None),
                        limit: int = Query(100, ge=1, le=1000),
                        user=Depends(require_super_admin)):
    ts = request.app.state.transaction_store
    if workspace_id:
        txs = ts.list_for_workspace(workspace_id, limit=limit, kind=kind)
    else:
        txs = (ts.list_all(limit=limit, kind=kind)
                if hasattr(ts, "list_all") else [])
    return {"transactions": [tx.to_dict() for tx in txs]}


@router.patch("/admin/users/{user_id}/super-admin")
def set_super_admin(user_id: str, req: SetSuperAdminReq,
                      request: Request,
                      user=Depends(require_super_admin)):
    locale = get_request_locale(request)
    us = request.app.state.user_store
    if user_id != req.user_id:
        raise HTTPException(400, "user_id mismatch")
    target = us.get(user_id)
    if not target:
        raise HTTPException(404, t("auth.user_not_found", locale=locale))
    us.update(user_id, is_super_admin=req.is_super_admin)
    refreshed = us.get(user_id)
    return refreshed.to_safe_dict()


__all__ = ["router"]
