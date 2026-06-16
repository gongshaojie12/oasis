# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""Verification code lifecycle: issue → store → verify (with TTL + rate limit).

Used for both email & SMS code flows. Same schema.
"""
from __future__ import annotations

import random
import string
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Literal
from urllib.parse import urlparse

import bcrypt


CHANNEL = Literal["email", "phone"]
PURPOSE = Literal["verify", "login", "reset_password"]

# 6-digit numeric code (industry standard, easy to type)
CODE_LENGTH = 6
TTL_MINUTES = 10
MAX_ATTEMPTS_PER_CODE = 5
MAX_SENDS_PER_HOUR = 5


@dataclass
class VerificationCode:
    code_id: str
    channel: str          # "email" | "phone"
    identifier: str       # the email or phone
    purpose: str          # "verify" | "login" | "reset_password"
    code_hash: str        # bcrypt hash of the raw code
    expires_at: datetime
    attempts: int = 0
    consumed_at: datetime | None = None
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc))


def generate_code(length: int = CODE_LENGTH) -> str:
    """6-digit numeric, e.g. ``'482917'``. Always exactly ``length`` chars."""
    return "".join(random.choices(string.digits, k=length))


def hash_code(code: str) -> str:
    """Salt + hash so DB leak doesn't reveal codes."""
    return bcrypt.hashpw(code.encode("utf-8"),
                          bcrypt.gensalt(rounds=8)).decode("utf-8")


def verify_code(raw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(raw.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


class InMemoryVerificationStore:
    def __init__(self):
        self._codes: dict[str, VerificationCode] = {}
        self._lock = Lock()

    def create(self, vc: VerificationCode) -> VerificationCode:
        if vc.code_id == "auto":
            vc.code_id = uuid.uuid4().hex
        with self._lock:
            self._codes[vc.code_id] = vc
        return vc

    def count_recent_sends(self, channel: str, identifier: str,
                             *, since: datetime) -> int:
        with self._lock:
            return sum(1 for c in self._codes.values()
                        if c.channel == channel
                        and c.identifier == identifier
                        and c.created_at >= since)

    def latest_active(self, channel: str, identifier: str,
                        purpose: str) -> VerificationCode | None:
        """Most recent un-expired, un-consumed code for channel+id+purpose."""
        now = datetime.now(timezone.utc)
        with self._lock:
            candidates = [c for c in self._codes.values()
                          if c.channel == channel
                          and c.identifier == identifier
                          and c.purpose == purpose
                          and c.consumed_at is None
                          and c.expires_at > now
                          and c.attempts < MAX_ATTEMPTS_PER_CODE]
        if not candidates:
            return None
        return max(candidates, key=lambda c: c.created_at)

    def increment_attempts(self, code_id: str) -> int:
        with self._lock:
            c = self._codes.get(code_id)
            if c:
                c.attempts += 1
                return c.attempts
            return 0

    def consume(self, code_id: str) -> bool:
        with self._lock:
            c = self._codes.get(code_id)
            if not c or c.consumed_at:
                return False
            c.consumed_at = datetime.now(timezone.utc)
            return True


def make_verification_store(dsn: str | None, *, eager_init: bool = True):
    if not dsn:
        return InMemoryVerificationStore()
    parsed = urlparse(dsn)
    scheme = (parsed.scheme or "").lower()
    # Windows raw path C:\foo\bar.db -> scheme='c'; treat as path.
    if len(scheme) == 1 and scheme.isalpha():
        scheme = ""
    if scheme in ("postgresql", "postgres"):
        from wanxiang.api.verification_store_pg import PgVerificationStore
        return PgVerificationStore(dsn, eager_init=eager_init)
    if scheme == "sqlite":
        path = parsed.path or dsn[len("sqlite:"):]
        if path.startswith("/") and len(path) > 2 and path[2] == ":":
            path = path[1:]
        from wanxiang.api.verification_store_sqlite import (
            SqliteVerificationStore)
        return SqliteVerificationStore(path)
    if not scheme:
        from wanxiang.api.verification_store_sqlite import (
            SqliteVerificationStore)
        return SqliteVerificationStore(dsn)
    raise ValueError(
        f"unsupported verification store DSN scheme: {scheme!r}")


__all__ = [
    "VerificationCode", "CODE_LENGTH", "TTL_MINUTES",
    "MAX_ATTEMPTS_PER_CODE", "MAX_SENDS_PER_HOUR",
    "generate_code", "hash_code", "verify_code",
    "InMemoryVerificationStore", "make_verification_store",
]
