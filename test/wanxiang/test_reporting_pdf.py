# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""M6+: PDF 导出 — render_markdown → PDF bytes via reportlab."""
from __future__ import annotations

import pytest

from wanxiang.reporting import pdf as pdf_module


_has_reportlab = pdf_module.REPORTLAB_AVAILABLE

pytestmark = pytest.mark.skipif(
    not _has_reportlab, reason="reportlab not installed")


def test_render_pdf_returns_pdf_bytes():
    out = pdf_module.render_pdf("Hello world")
    assert isinstance(out, bytes)
    assert out.startswith(b"%PDF-")


def test_render_pdf_handles_plain_text():
    out = pdf_module.render_pdf("This is a paragraph with words.")
    assert out.startswith(b"%PDF-")
    assert len(out) > 500


def test_render_pdf_handles_headings():
    md = "# 大标题\n\n## 副标题\n\n正文段落。"
    out = pdf_module.render_pdf(md)
    assert out.startswith(b"%PDF-")


def test_render_pdf_handles_tables():
    md = "| 因素 | 影响 |\n|---|---|\n| 价格 | 高 |\n| 渠道 | 中 |"
    out = pdf_module.render_pdf(md)
    assert out.startswith(b"%PDF-")


def test_render_pdf_handles_bullets():
    md = "要点：\n- 第一\n- 第二\n- 第三"
    out = pdf_module.render_pdf(md)
    assert out.startswith(b"%PDF-")


def test_render_pdf_handles_chinese_without_crashing():
    md = ("# 万象模拟报告\n\n"
          "群体整体偏正面（均值 6.8），但价格阻力明显，"
          "主要劝退原因为「价格偏高」。\n\n"
          "## 反事实推演\n\n"
          "若降价到 ¥5，购买意愿均值预计提升至 7.4。")
    out = pdf_module.render_pdf(md)
    assert out.startswith(b"%PDF-")
    assert len(out) > 1000


def test_render_pdf_raises_when_reportlab_missing(monkeypatch):
    monkeypatch.setattr(pdf_module, "REPORTLAB_AVAILABLE", False)
    with pytest.raises(RuntimeError, match="reportlab"):
        pdf_module.render_pdf("anything")
