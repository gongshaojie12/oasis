# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""P1: JWT issue/decode unit tests."""
from __future__ import annotations

import time

from wanxiang.api.auth_jwt import (
    decode_token,
    issue_access_token,
    issue_refresh_token,
)


SECRET = "test-secret-must-be-32-bytes-min-xxxxxxxxxx"


def test_issue_access_decode_roundtrip():
    tok = issue_access_token(user_id="u1", secret=SECRET, ttl_minutes=5)
    claims = decode_token(tok, secret=SECRET)
    assert claims is not None
    assert claims["sub"] == "u1"
    assert claims["type"] == "access"


def test_issue_refresh_returns_token_and_jti():
    tok, jti = issue_refresh_token(user_id="u1", secret=SECRET, ttl_days=1)
    assert tok and isinstance(jti, str) and len(jti) >= 16
    claims = decode_token(tok, secret=SECRET)
    assert claims["type"] == "refresh"
    assert claims["jti"] == jti


def test_decode_wrong_secret_returns_none():
    tok = issue_access_token(user_id="u1", secret=SECRET, ttl_minutes=5)
    assert decode_token(tok, secret="some-other-secret-xxxxxxxxxxxxxx") is None


def test_decode_garbage_returns_none():
    assert decode_token("not.a.jwt", secret=SECRET) is None


def test_decode_expected_type_mismatch():
    access = issue_access_token(user_id="u1", secret=SECRET, ttl_minutes=5)
    assert decode_token(access, secret=SECRET, expected_type="refresh") is None
    refresh, _ = issue_refresh_token(user_id="u1", secret=SECRET, ttl_days=1)
    assert decode_token(refresh, secret=SECRET, expected_type="access") is None


def test_decode_expired_token():
    # Negative TTL = already expired
    tok = issue_access_token(user_id="u1", secret=SECRET, ttl_minutes=-1)
    # python-jose uses iat/exp; expired -> None
    assert decode_token(tok, secret=SECRET) is None


def test_access_token_type_field():
    tok = issue_access_token(user_id="u1", secret=SECRET)
    claims = decode_token(tok, secret=SECRET)
    assert claims["type"] == "access"
    assert claims["sub"] == "u1"


def test_refresh_token_type_field():
    tok, _jti = issue_refresh_token(user_id="u1", secret=SECRET)
    claims = decode_token(tok, secret=SECRET)
    assert claims["type"] == "refresh"


def test_access_token_extra_payload():
    tok = issue_access_token(user_id="u1", secret=SECRET,
                              extra={"workspace_id": "w1"})
    claims = decode_token(tok, secret=SECRET)
    assert claims.get("workspace_id") == "w1"
