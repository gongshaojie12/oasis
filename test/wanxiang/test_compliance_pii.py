# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""PII detection + redaction."""
import pytest

from wanxiang.compliance.pii import find_pii, redact_text, redact_report


def test_detects_cn_phone():
    hits = find_pii("打 13800138000 给我")
    assert any(h.kind == "phone_cn" for h in hits)


def test_detects_email():
    hits = find_pii("发到 user@example.com")
    assert any(h.kind == "email" for h in hits)


def test_detects_cn_id_card_18digit():
    # Valid 18-digit pattern (year 1990, month 01, day 15)
    text = "身份证号 11010119900115001X"
    hits = find_pii(text)
    assert any(h.kind == "id_card" for h in hits)


def test_detects_bank_card_16digit():
    hits = find_pii("银行卡 6228480402564890018")
    assert any(h.kind == "bank_card" for h in hits)


def test_no_false_positive_on_normal_text():
    assert find_pii("你好世界") == []
    assert find_pii("评分是 7 分") == []
    assert find_pii("year 2026 month 06") == []


def test_redact_text_replaces_with_token():
    out = redact_text("call me at 13800138000")
    assert "13800138000" not in out
    assert "[REDACTED:phone_cn]" in out


def test_redact_text_multiple_in_one_string():
    out = redact_text("phone 13800138000, email a@b.com")
    assert "13800138000" not in out
    assert "a@b.com" not in out
    assert out.count("[REDACTED:") == 2


def test_redact_text_empty():
    assert redact_text("") == ""
    assert redact_text(None) is None


def test_redact_text_no_pii_returns_unchanged():
    assert redact_text("clean text 你好") == "clean text 你好"


def test_id_card_takes_priority_over_bank_card():
    """An 18-digit ID card should not be redacted as bank_card."""
    text = "11010119900115001X"
    hits = find_pii(text)
    assert len(hits) == 1
    assert hits[0].kind == "id_card"


def test_redact_report_walks_nested():
    rep = {
        "summary": "联系 user@example.com",
        "items": [{"note": "拨 13800138000"}],
        "n": 42,
    }
    out = redact_report(rep)
    assert "user@example.com" not in out["summary"]
    assert "13800138000" not in out["items"][0]["note"]
    assert out["n"] == 42  # numbers untouched


def test_redact_report_input_not_mutated():
    rep = {"x": "13800138000"}
    redact_report(rep)
    assert rep["x"] == "13800138000"
