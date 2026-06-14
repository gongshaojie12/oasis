# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""reporting: 报告生成器（spec §M6，接 chat.html 工件卡 + PDF 导出）。

M6+ 扩展:
- rejection: 劝退原因构成（关键词桶）
- trajectory: 群体情绪演化（多轮社交）
- commentary: LLM 自然语言执行摘要
- pdf: 报告 PDF 导出
"""
from wanxiang.reporting.commentary import generate_commentary
from wanxiang.reporting.pdf import REPORTLAB_AVAILABLE, render_pdf
from wanxiang.reporting.rejection import (DEFAULT_BUCKET, REJECTION_BUCKETS,
                                            analyze_rejection_reasons,
                                            bucket_reason)
from wanxiang.reporting.report import build_report, render_markdown
from wanxiang.reporting.trajectory import TrajectoryPoint, build_trajectory

__all__ = [
    "build_report", "render_markdown",
    "analyze_rejection_reasons", "bucket_reason",
    "REJECTION_BUCKETS", "DEFAULT_BUCKET",
    "TrajectoryPoint", "build_trajectory",
    "generate_commentary",
    "render_pdf", "REPORTLAB_AVAILABLE",
]
