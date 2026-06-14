# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""PII detection + redaction (M3-12).

中国语境的常见 PII:
- 手机号: 1[3-9]\\d{9}
- 身份证: 18-digit (前 17 数字 + X|0-9)
- 银行卡: 13-19 位数字
- 邮箱

顺序很重要：先匹配长且严格的（身份证 > 银行卡 > 手机），后匹配短的。
重叠时，靠前匹配（更长/更严格）优先。
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Patterns are tried top-to-bottom; first hit wins on overlap.
_PII_PATTERNS = [
    ("id_card",
     re.compile(r"(?<!\d)[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])"
                r"(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx](?!\d)")),
    ("bank_card",
     re.compile(r"(?<!\d)\d{13,19}(?!\d)")),
    ("phone_cn",
     re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")),
    ("email",
     re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
]

REDACT_TOKEN = "[REDACTED:{kind}]"


@dataclass(frozen=True)
class PIIHit:
    kind: str       # "id_card" | "bank_card" | "phone_cn" | "email"
    value: str
    start: int
    end: int


def find_pii(text: str) -> list[PIIHit]:
    """Return all PII hits in `text`, sorted by position. Overlapping matches
    resolved by pattern priority (earlier pattern wins)."""
    if not text:
        return []
    hits: list[PIIHit] = []
    occupied: list[tuple[int, int]] = []
    for kind, pat in _PII_PATTERNS:
        for m in pat.finditer(text):
            s, e = m.span()
            # Skip if overlaps already-matched range (higher-priority kinds win)
            if any(not (e <= os_ or s >= oe) for os_, oe in occupied):
                continue
            hits.append(PIIHit(kind=kind, value=m.group(), start=s, end=e))
            occupied.append((s, e))
    return sorted(hits, key=lambda h: h.start)


def redact_text(text):
    """Return `text` with all detected PII replaced by [REDACTED:<kind>].

    Empty string / None are returned unchanged.
    """
    if text is None:
        return None
    if not text:
        return text
    hits = find_pii(text)
    if not hits:
        return text
    out = []
    cursor = 0
    for h in hits:
        out.append(text[cursor:h.start])
        out.append(REDACT_TOKEN.format(kind=h.kind))
        cursor = h.end
    out.append(text[cursor:])
    return "".join(out)


def redact_report(report):
    """Walk a report dict, redact PII in all string leaves. Returns a NEW dict
    (immutable input)."""
    def walk(node):
        if isinstance(node, str):
            return redact_text(node)
        if isinstance(node, dict):
            return {k: walk(v) for k, v in node.items()}
        if isinstance(node, list):
            return [walk(x) for x in node]
        if isinstance(node, tuple):
            return tuple(walk(x) for x in node)
        return node
    return walk(report)
