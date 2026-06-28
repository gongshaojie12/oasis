# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""文档解析 docparse:文本/pdf/docx/xlsx 提取 + 截断 + 错误。"""
from __future__ import annotations

import asyncio
import io

import pytest

from wanxiang.chat import docparse


def test_kind_of():
    assert docparse.kind_of("a.txt") == "text"
    assert docparse.kind_of("a.pdf") == "text"
    assert docparse.kind_of("a.PNG") == "image"
    assert docparse.kind_of("a.exe") == "unsupported"


def test_extract_txt_and_csv():
    assert "你好" in docparse.extract_text("a.txt", "你好世界".encode("utf-8"))
    csv = "name,price\n气泡水,6".encode("utf-8")
    assert "气泡水" in docparse.extract_text("a.csv", csv)


def test_extract_truncates():
    big = ("x" * (docparse.MAX_EXTRACT_CHARS + 5000)).encode("utf-8")
    out = docparse.extract_text("a.txt", big)
    assert len(out) <= docparse.MAX_EXTRACT_CHARS + 50
    assert "截断" in out


def test_extract_docx():
    docx = pytest.importorskip("docx")
    d = docx.Document()
    d.add_paragraph("新品气泡水")
    d.add_paragraph("定价 6 元")
    buf = io.BytesIO()
    d.save(buf)
    text = docparse.extract_text("a.docx", buf.getvalue())
    assert "气泡水" in text and "6" in text


def test_extract_xlsx():
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["产品", "价格"])
    ws.append(["气泡水", 6])
    buf = io.BytesIO()
    wb.save(buf)
    text = docparse.extract_text("a.xlsx", buf.getvalue())
    assert "气泡水" in text


def test_extract_pdf_minimal():
    # 用 reportlab 生成一个含文字的最小 PDF(运行时已装 reportlab)
    reportlab = pytest.importorskip("reportlab")
    _ = reportlab
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(100, 700, "Sparkling Water Product")
    c.save()
    text = docparse.extract_text("a.pdf", buf.getvalue())
    assert "Sparkling" in text or "Water" in text


def test_unsupported_raises():
    with pytest.raises(docparse.DocParseError):
        docparse.extract_text("a.zip", b"x")


def test_distill_material_uses_model():
    async def fake_call(messages):
        # 回显:验证素材正文确实传给了模型
        assert any("气泡水" in str(m.get("content", "")) for m in messages)
        return "提炼后的素材:气泡水"
    out = asyncio.run(docparse.distill_material("产品是气泡水", fake_call))
    assert "气泡水" in out
