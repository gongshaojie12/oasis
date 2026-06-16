# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""P2: SqliteVerificationStore persistence tests."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta


def _mk_vc(channel="email", identifier="a@b.com", purpose="verify",
            code="123456", ttl_min=10):
    from wanxiang.api.verification import VerificationCode, hash_code

    return VerificationCode(
        code_id="auto", channel=channel, identifier=identifier,
        purpose=purpose, code_hash=hash_code(code),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=ttl_min),
    )


def test_sqlite_create_and_latest_active_roundtrip(tmp_path):
    from wanxiang.api.verification import make_verification_store

    db = str(tmp_path / "verify.db")
    s = make_verification_store(db)
    vc = s.create(_mk_vc())
    assert vc.code_id and vc.code_id != "auto"
    got = s.latest_active("email", "a@b.com", "verify")
    assert got is not None and got.code_id == vc.code_id


def test_sqlite_persistence_across_reopen(tmp_path):
    from wanxiang.api.verification import make_verification_store

    db = str(tmp_path / "verify.db")
    s1 = make_verification_store(db)
    vc = s1.create(_mk_vc())
    cid = vc.code_id

    s2 = make_verification_store(db)
    got = s2.latest_active("email", "a@b.com", "verify")
    assert got is not None and got.code_id == cid


def test_sqlite_count_recent_sends_time_window(tmp_path):
    from wanxiang.api.verification import make_verification_store

    db = str(tmp_path / "verify.db")
    s = make_verification_store(db)
    s.create(_mk_vc())
    s.create(_mk_vc())
    since = datetime.now(timezone.utc) - timedelta(hours=1)
    assert s.count_recent_sends("email", "a@b.com", since=since) == 2
    # Future window -> 0
    future_since = datetime.now(timezone.utc) + timedelta(hours=1)
    assert s.count_recent_sends("email", "a@b.com", since=future_since) == 0


def test_sqlite_consume_marks_consumed_at(tmp_path):
    from wanxiang.api.verification import make_verification_store

    db = str(tmp_path / "verify.db")
    s = make_verification_store(db)
    vc = s.create(_mk_vc())
    assert s.consume(vc.code_id) is True
    # Second consume on same row is a no-op
    assert s.consume(vc.code_id) is False
    # No longer active
    assert s.latest_active("email", "a@b.com", "verify") is None


def test_sqlite_increment_attempts_persists(tmp_path):
    from wanxiang.api.verification import make_verification_store

    db = str(tmp_path / "verify.db")
    s = make_verification_store(db)
    vc = s.create(_mk_vc())
    assert s.increment_attempts(vc.code_id) == 1
    assert s.increment_attempts(vc.code_id) == 2
    # Re-open and verify the counter persisted
    s2 = make_verification_store(db)
    assert s2.increment_attempts(vc.code_id) == 3
