# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""POST /v1/reports/pdf —— M6+ 报告 PDF 导出。

输入二选一：
- markdown: 任意 markdown 字符串（前端直接喂）
- task_id: 已完成异步模拟任务的 ID（从 task_store 取 result.markdown）

任意一个都必须；两个都给 → 400。任务不存在或非自己 → 404；任务未完成 → 409。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from wanxiang.api.auth import require_tenant
from wanxiang.api.i18n import get_request_locale, t
from wanxiang.api.tasks import TaskStatus, TaskStore
from wanxiang.api.tenancy import TenantInfo
from wanxiang.reporting import render_pdf

router = APIRouter()


class PdfRequest(BaseModel):
    markdown: str | None = None
    task_id: str | None = None


def _store(request: Request) -> TaskStore:
    return request.app.state.task_store


@router.post("/reports/pdf")
def report_pdf(
    body: PdfRequest,
    request: Request,
    tenant: TenantInfo = Depends(require_tenant),
):
    loc = get_request_locale(request)
    md = body.markdown
    task_id = body.task_id
    if bool(md) == bool(task_id):
        raise HTTPException(
            status_code=400,
            detail=t("report.bad_request_xor", locale=loc))

    if task_id:
        store = _store(request)
        task = store.get(tenant.tenant_id, task_id)
        if task is None:
            raise HTTPException(
                status_code=404,
                detail=t("request.task_not_found", locale=loc))
        if task.status != TaskStatus.DONE:
            raise HTTPException(
                status_code=409,
                detail=t("report.task_not_done", locale=loc,
                         status=task.status.value))
        result = task.result
        if result is None or not getattr(result, "markdown", None):
            raise HTTPException(
                status_code=409,
                detail=t("report.task_has_no_markdown", locale=loc))
        md = result.markdown

    try:
        pdf_bytes = render_pdf(md)
    except RuntimeError as e:
        # reportlab not installed in this deploy
        raise HTTPException(
            status_code=503,
            detail=t("report.pdf_unavailable", locale=loc, reason=str(e)))

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="report.pdf"',
        },
    )
