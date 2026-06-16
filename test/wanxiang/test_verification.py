# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""P2: VerificationCode model + InMemoryVerificationStore."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta


def test_generate_code_is_6_digit_numeric():
    from wanxiang.api.verification import generate_code, CODE_LENGTH

    for _ in range(20):
        code = generate_code()
        assert len(code) == CODE_LENGTH == 6
        assert code.isdigit()


def test_hash_code_verify_round_trip():
    from wanxiang.api.verification import hash_code, verify_code

    h = hash_code("482917")
    assert h != "482917"
    assert verify_code("482917", h) is True


def test_verify_code_wrong_returns_false():
    from wanxiang.api.verification import hash_code, verify_code

    h = hash_code("482917")
    assert verify_code("000000", h) is False
    assert verify_code("", h) is False


def _mk_vc(channel="email", identifier="a@b.com", purpose="verify",
            code="123456", ttl_min=10):
    from wanxiang.api.verification import VerificationCode, hash_code

    return VerificationCode(
        code_id="auto", channel=channel, identifier=identifier,
        purpose=purpose, code_hash=hash_code(code),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=ttl_min),
    )


def test_store_create_and_latest_active_roundtrip():
    from wanxiang.api.verification import InMemoryVerificationStore

    s = InMemoryVerificationStore()
    vc = s.create(_mk_vc())
    assert vc.code_id and vc.code_id != "auto"
    got = s.latest_active("email", "a@b.com", "verify")
    assert got is not None and got.code_id == vc.code_id


def test_latest_active_returns_none_if_expired():
    from wanxiang.api.verification import InMemoryVerificationStore

    s = InMemoryVerificationStore()
    s.create(_mk_vc(ttl_min=-1))
    assert s.latest_active("email", "a@b.com", "verify") is None


def test_latest_active_returns_none_if_consumed():
    from wanxiang.api.verification import InMemoryVerificationStore

    s = InMemoryVerificationStore()
    vc = s.create(_mk_vc())
    assert s.consume(vc.code_id) is True
    assert s.latest_active("email", "a@b.com", "verify") is None


def test_latest_active_returns_none_if_attempts_exhausted():
    from wanxiang.api.verification import (InMemoryVerificationStore,
                                              MAX_ATTEMPTS_PER_CODE)

    s = InMemoryVerificationStore()
    vc = s.create(_mk_vc())
    for _ in range(MAX_ATTEMPTS_PER_CODE):
        s.increment_attempts(vc.code_id)
    assert s.latest_active("email", "a@b.com", "verify") is None


def test_count_recent_sends_within_window():
    from wanxiang.api.verification import InMemoryVerificationStore

    s = InMemoryVerificationStore()
    s.create(_mk_vc())
    s.create(_mk_vc())
    since = datetime.now(timezone.utc) - timedelta(hours=1)
    assert s.count_recent_sends("email", "a@b.com", since=since) == 2
    # Different identifier counted separately
    assert s.count_recent_sends("email", "c@d.com", since=since) == 0


def test_increment_attempts_increases_counter():
    from wanxiang.api.verification import InMemoryVerificationStore

    s = InMemoryVerificationStore()
    vc = s.create(_mk_vc())
    assert s.increment_attempts(vc.code_id) == 1
    assert s.increment_attempts(vc.code_id) == 2


def test_consume_idempotent_second_returns_false():
    from wanxiang.api.verification import InMemoryVerificationStore

    s = InMemoryVerificationStore()
    vc = s.create(_mk_vc())
    assert s.consume(vc.code_id) is True
    assert s.consume(vc.code_id) is False
