# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""M6+: PDF 导出。

把 markdown 字符串渲染成 PDF bytes。无外部二进制依赖，纯 Python：
reportlab + 内置 STSong-Light CIDFont（支持简体中文）。

支持的 markdown 子集：
- # / ## / ### 标题
- 段落（空行分隔）
- - 列表项
- | 表头 | ... | + |---|---| 分隔行 + | 数据行 |
- 其它行当成普通段落

不支持：链接 / 图片 / 代码块（出现 ``` 会按普通文本处理）。
"""
from __future__ import annotations

import io
import re
from typing import Any

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer,
                                      Table, TableStyle)
    REPORTLAB_AVAILABLE = True
except ImportError:  # pragma: no cover
    REPORTLAB_AVAILABLE = False


_CJK_FONT_NAME = "STSong-Light"
_CJK_FONT_REGISTERED = False


def _ensure_font_registered() -> None:
    """注册内置 CJK CIDFont（首次调用时）。"""
    global _CJK_FONT_REGISTERED
    if _CJK_FONT_REGISTERED:
        return
    pdfmetrics.registerFont(UnicodeCIDFont(_CJK_FONT_NAME))
    _CJK_FONT_REGISTERED = True


def _make_styles() -> dict[str, Any]:
    """构造 CJK-aware paragraph styles."""
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "CnTitle", parent=base["Title"],
            fontName=_CJK_FONT_NAME, fontSize=20, leading=26,
            spaceAfter=12),
        "h2": ParagraphStyle(
            "CnH2", parent=base["Heading2"],
            fontName=_CJK_FONT_NAME, fontSize=15, leading=20,
            spaceBefore=10, spaceAfter=6),
        "h3": ParagraphStyle(
            "CnH3", parent=base["Heading3"],
            fontName=_CJK_FONT_NAME, fontSize=12, leading=16,
            spaceBefore=8, spaceAfter=4),
        "body": ParagraphStyle(
            "CnBody", parent=base["BodyText"],
            fontName=_CJK_FONT_NAME, fontSize=10.5, leading=15,
            spaceAfter=4),
        "bullet": ParagraphStyle(
            "CnBullet", parent=base["BodyText"],
            fontName=_CJK_FONT_NAME, fontSize=10.5, leading=15,
            leftIndent=14, bulletIndent=4, spaceAfter=2),
        "table_cell": ParagraphStyle(
            "CnTableCell", parent=base["BodyText"],
            fontName=_CJK_FONT_NAME, fontSize=9.5, leading=12),
    }


_TABLE_ROW_RE = re.compile(r"^\s*\|(.+)\|\s*$")
_TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$")


def _split_table_row(line: str) -> list[str]:
    inner = line.strip().strip("|")
    return [c.strip() for c in inner.split("|")]


def _escape_xml(text: str) -> str:
    """转义 reportlab Paragraph 用的 XML-like 文本。"""
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;"))


def _flush_paragraph(buf: list[str], story: list, styles: dict) -> None:
    if not buf:
        return
    text = " ".join(s.strip() for s in buf if s.strip())
    if text:
        story.append(Paragraph(_escape_xml(text), styles["body"]))
    buf.clear()


def _build_story(markdown_text: str, styles: dict) -> list:
    lines = markdown_text.splitlines()
    story: list = []
    para_buf: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # blank → flush paragraph
        if not stripped:
            _flush_paragraph(para_buf, story, styles)
            story.append(Spacer(1, 4))
            i += 1
            continue

        # heading
        if stripped.startswith("### "):
            _flush_paragraph(para_buf, story, styles)
            story.append(Paragraph(_escape_xml(stripped[4:]), styles["h3"]))
            i += 1
            continue
        if stripped.startswith("## "):
            _flush_paragraph(para_buf, story, styles)
            story.append(Paragraph(_escape_xml(stripped[3:]), styles["h2"]))
            i += 1
            continue
        if stripped.startswith("# "):
            _flush_paragraph(para_buf, story, styles)
            story.append(Paragraph(_escape_xml(stripped[2:]), styles["title"]))
            i += 1
            continue

        # horizontal rule
        if stripped in ("---", "***", "___"):
            _flush_paragraph(para_buf, story, styles)
            story.append(Spacer(1, 6))
            i += 1
            continue

        # table: header row, then separator, then data
        if _TABLE_ROW_RE.match(line):
            # try to collect a table
            header_cells = _split_table_row(line)
            if (i + 1 < len(lines)
                    and _TABLE_SEP_RE.match(lines[i + 1].strip())):
                _flush_paragraph(para_buf, story, styles)
                rows = [header_cells]
                j = i + 2
                while j < len(lines) and _TABLE_ROW_RE.match(lines[j]):
                    rows.append(_split_table_row(lines[j]))
                    j += 1
                # build table; wrap cells in Paragraph for wrapping + CJK
                wrapped = [
                    [Paragraph(_escape_xml(c), styles["table_cell"])
                     for c in row]
                    for row in rows
                ]
                tbl = Table(wrapped, hAlign="LEFT")
                tbl.setStyle(TableStyle([
                    ("FONT", (0, 0), (-1, -1), _CJK_FONT_NAME, 9.5),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]))
                story.append(tbl)
                story.append(Spacer(1, 6))
                i = j
                continue
            # otherwise treat as text

        # bullet list item
        if stripped.startswith("- ") or stripped.startswith("* "):
            _flush_paragraph(para_buf, story, styles)
            content = stripped[2:]
            # bullet 用 &bull; 字符
            story.append(Paragraph(
                "• " + _escape_xml(content), styles["bullet"]))
            i += 1
            continue

        # ordered list
        if re.match(r"^\d+\.\s+", stripped):
            _flush_paragraph(para_buf, story, styles)
            story.append(Paragraph(_escape_xml(stripped), styles["bullet"]))
            i += 1
            continue

        # default: paragraph text
        para_buf.append(stripped)
        i += 1

    _flush_paragraph(para_buf, story, styles)
    return story


def render_pdf(markdown_text: str, *,
                title: str = "万象 模拟报告") -> bytes:
    """渲染 markdown 为 PDF bytes。失败时若 reportlab 缺失抛 RuntimeError。"""
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError(
            "PDF export requires reportlab. pip install reportlab")

    _ensure_font_registered()
    styles = _make_styles()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, title=title,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
    )
    story = _build_story(markdown_text, styles)
    if not story:
        # 空内容也得有点东西，避免 reportlab 报错
        story = [Paragraph(_escape_xml(title), styles["title"])]
    doc.build(story)
    return buffer.getvalue()
