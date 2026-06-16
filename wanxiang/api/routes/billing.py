# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""P4: workspace-scoped billing routes.

GET /v1/workspaces/{slug}/balance       -> current balance
GET /v1/workspaces/{slug}/transactions  -> recent balance changes

Both require the requester is a member of the workspace.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from wanxiang.api.auth_user import require_user
from wanxiang.api.i18n import get_request_locale, t

router = APIRouter()


def _require_member(request: Request, workspace_id: str,
                      user_id: str, locale: str):
    m = request.app.state.workspace_store.get_member(workspace_id, user_id)
    if not m:
        raise HTTPException(
            403, t("workspace.not_a_member", locale=locale))
    return m


@router.get("/workspaces/{slug}/balance")
def workspace_balance(slug: str, request: Request,
                        user=Depends(require_user)):
    locale = get_request_locale(request)
    ws = request.app.state.workspace_store.get_by_slug(slug)
    if not ws:
        raise HTTPException(404, t("workspace.not_found", locale=locale))
    _require_member(request, ws.workspace_id, user.user_id, locale)
    return {
        "workspace_id": ws.workspace_id,
        "slug": ws.slug,
        "balance_cost_units": ws.balance_cost_units,
        "monthly_budget": ws.monthly_budget,
    }


@router.get("/workspaces/{slug}/transactions")
def workspace_transactions(slug: str, request: Request,
                              limit: int = Query(50, ge=1, le=500),
                              kind: str | None = Query(None),
                              user=Depends(require_user)):
    locale = get_request_locale(request)
    ws = request.app.state.workspace_store.get_by_slug(slug)
    if not ws:
        raise HTTPException(404, t("workspace.not_found", locale=locale))
    _require_member(request, ws.workspace_id, user.user_id, locale)
    txs = request.app.state.transaction_store.list_for_workspace(
        ws.workspace_id, limit=limit, kind=kind)
    return {"transactions": [tx.to_dict() for tx in txs]}


__all__ = ["router"]
