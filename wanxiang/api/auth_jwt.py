# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""JWT access + refresh token issuance & verification (P1).

Uses ``python-jose`` (HS256 by default). Refresh tokens carry a ``jti``
claim for future blacklisting (Redis-backed in P2+).
"""
from __future__ import annotations

import secrets as _secrets
from datetime import datetime, timedelta, timezone
from typing import Literal

from jose import JWTError, jwt


def issue_access_token(*, user_id: str, secret: str, alg: str = "HS256",
                        ttl_minutes: int = 15,
                        extra: dict | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ttl_minutes)).timestamp()),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, secret, algorithm=alg)


def issue_refresh_token(*, user_id: str, secret: str, alg: str = "HS256",
                         ttl_days: int = 7,
                         jti: str | None = None) -> tuple[str, str]:
    """Returns ``(token, jti)``. The ``jti`` is suitable for blacklisting."""
    jti = jti or _secrets.token_hex(16)
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "type": "refresh",
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=ttl_days)).timestamp()),
    }
    return jwt.encode(payload, secret, algorithm=alg), jti


def decode_token(token: str, *, secret: str, alg: str = "HS256",
                  expected_type: Literal["access", "refresh"] | None = None
                  ) -> dict | None:
    """Return claims dict, or ``None`` if invalid/expired/wrong type."""
    try:
        claims = jwt.decode(token, secret, algorithms=[alg])
    except JWTError:
        return None
    if expected_type and claims.get("type") != expected_type:
        return None
    return claims


__all__ = ["issue_access_token", "issue_refresh_token", "decode_token"]
