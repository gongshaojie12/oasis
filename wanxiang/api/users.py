# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""User account model + stores (P1).

Provides:
  * ``User`` dataclass (no password_hash leak via ``to_safe_dict``)
  * ``hash_password`` / ``verify_password`` / ``validate_password`` helpers
  * ``InMemoryUserStore`` for tests / dev
  * ``make_user_store(dsn)`` factory dispatching to sqlite / pg backends

JWT issuance lives in ``auth_jwt.py``; routes in ``routes/auth.py``.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from urllib.parse import urlparse

import bcrypt


EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$")
PHONE_CN_RE = re.compile(r"^1[3-9]\d{9}$")


@dataclass
class User:
    user_id: str
    email: str | None
    phone: str | None
    password_hash: str
    display_name: str
    locale: str = "zh"
    avatar_url: str | None = None
    email_verified: bool = False
    phone_verified: bool = False
    is_super_admin: bool = False
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc))

    def to_safe_dict(self) -> dict:
        """Public-facing dict (no ``password_hash``)."""
        return {
            "user_id": self.user_id,
            "email": self.email,
            "phone": self.phone,
            "display_name": self.display_name,
            "locale": self.locale,
            "avatar_url": self.avatar_url,
            "email_verified": self.email_verified,
            "phone_verified": self.phone_verified,
            "is_super_admin": self.is_super_admin,
            "created_at": self.created_at.isoformat(),
        }


def hash_password(raw: str) -> str:
    return bcrypt.hashpw(raw.encode("utf-8"),
                          bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(raw.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def validate_password(raw: str) -> str | None:
    """Return an i18n catalog key or ``None`` if the password is OK."""
    if len(raw) < 8:
        return "auth.password_too_short"
    if not re.search(r"[a-zA-Z]", raw) or not re.search(r"\d", raw):
        return "auth.password_too_weak"
    return None


# ---- In-memory store ----

class InMemoryUserStore:
    def __init__(self):
        self._users: dict[str, User] = {}
        self._by_email: dict[str, str] = {}
        self._by_phone: dict[str, str] = {}
        self._lock = Lock()

    def create(self, user: User) -> User:
        if user.user_id == "auto":
            user.user_id = uuid.uuid4().hex
        with self._lock:
            if user.email and user.email.lower() in self._by_email:
                raise ValueError("email already exists")
            if user.phone and user.phone in self._by_phone:
                raise ValueError("phone already exists")
            self._users[user.user_id] = user
            if user.email:
                self._by_email[user.email.lower()] = user.user_id
            if user.phone:
                self._by_phone[user.phone] = user.user_id
        return user

    def get(self, user_id: str) -> User | None:
        return self._users.get(user_id)

    def get_by_email(self, email: str) -> User | None:
        uid = self._by_email.get(email.lower())
        return self._users.get(uid) if uid else None

    def get_by_phone(self, phone: str) -> User | None:
        uid = self._by_phone.get(phone)
        return self._users.get(uid) if uid else None

    def update(self, user_id: str, **fields) -> User | None:
        with self._lock:
            u = self._users.get(user_id)
            if not u:
                return None
            for k, v in fields.items():
                if hasattr(u, k):
                    setattr(u, k, v)
            return u


def make_user_store(dsn: str | None, *, eager_init: bool = True):
    """DSN dispatch: None|plain-path -> SQLite, sqlite:// -> SQLite,
    postgresql:// -> PG. Mirrors ``make_usage_store``.
    """
    if not dsn:
        return InMemoryUserStore()
    parsed = urlparse(dsn)
    scheme = (parsed.scheme or "").lower()
    # Windows raw path C:\foo\bar.db is parsed with scheme='c'; treat as path.
    if len(scheme) == 1 and scheme.isalpha():
        scheme = ""
    if scheme in ("postgresql", "postgres"):
        from wanxiang.api.user_store_pg import PgUserStore
        return PgUserStore(dsn, eager_init=eager_init)
    if scheme == "sqlite":
        path = parsed.path or dsn[len("sqlite:"):]
        if path.startswith("/") and len(path) > 2 and path[2] == ":":
            path = path[1:]
        from wanxiang.api.user_store_sqlite import SqliteUserStore
        return SqliteUserStore(path)
    if not scheme:
        from wanxiang.api.user_store_sqlite import SqliteUserStore
        return SqliteUserStore(dsn)
    raise ValueError(f"unsupported user store DSN scheme: {scheme!r}")


__all__ = [
    "User", "hash_password", "verify_password", "validate_password",
    "EMAIL_RE", "PHONE_CN_RE",
    "InMemoryUserStore", "make_user_store",
]
