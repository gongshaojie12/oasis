# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""PgUserStore (P1) — PG mirror of SqliteUserStore. Lazy psycopg import."""
from __future__ import annotations

import uuid
from datetime import datetime
from threading import Lock

from wanxiang.api.users import User

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    email TEXT,
    phone TEXT,
    password_hash TEXT NOT NULL,
    display_name TEXT NOT NULL,
    locale TEXT NOT NULL DEFAULT 'zh',
    avatar_url TEXT,
    email_verified INTEGER NOT NULL DEFAULT 0,
    phone_verified INTEGER NOT NULL DEFAULT 0,
    is_super_admin INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email
    ON users(email) WHERE email IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_phone
    ON users(phone) WHERE phone IS NOT NULL;
"""


def _row_to_user(row: dict) -> User:
    return User(
        user_id=row["user_id"],
        email=row["email"],
        phone=row["phone"],
        password_hash=row["password_hash"],
        display_name=row["display_name"],
        locale=row["locale"] or "zh",
        avatar_url=row["avatar_url"],
        email_verified=bool(row["email_verified"]),
        phone_verified=bool(row["phone_verified"]),
        is_super_admin=bool(row["is_super_admin"]),
        created_at=datetime.fromisoformat(row["created_at"]),
    )


class PgUserStore:
    def __init__(self, dsn: str, *, eager_init: bool = True):
        self.dsn = dsn
        self._lock = Lock()
        if eager_init:
            with self._connect() as conn:
                conn.execute(_SCHEMA)

    def _connect(self):
        import psycopg
        from psycopg.rows import dict_row
        return psycopg.connect(self.dsn, autocommit=True, row_factory=dict_row)

    def create(self, user: User) -> User:
        if user.user_id == "auto":
            user.user_id = uuid.uuid4().hex
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO users "
                "(user_id, email, phone, password_hash, display_name, "
                " locale, avatar_url, email_verified, phone_verified, "
                " is_super_admin, created_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (user.user_id, user.email, user.phone, user.password_hash,
                 user.display_name, user.locale, user.avatar_url,
                 int(user.email_verified), int(user.phone_verified),
                 int(user.is_super_admin), user.created_at.isoformat()))
        return user

    def get(self, user_id: str) -> User | None:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM users WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
        return _row_to_user(row) if row else None

    def get_by_email(self, email: str) -> User | None:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM users WHERE LOWER(email) = LOWER(%s)",
                (email,))
            row = cur.fetchone()
        return _row_to_user(row) if row else None

    def get_by_phone(self, phone: str) -> User | None:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM users WHERE phone = %s", (phone,))
            row = cur.fetchone()
        return _row_to_user(row) if row else None

    def update(self, user_id: str, **fields) -> User | None:
        if not fields:
            return self.get(user_id)
        cols: list[str] = []
        vals: list = []
        for k, v in fields.items():
            if k in ("email", "phone", "password_hash", "display_name",
                     "locale", "avatar_url"):
                cols.append(f"{k} = %s")
                vals.append(v)
            elif k in ("email_verified", "phone_verified", "is_super_admin"):
                cols.append(f"{k} = %s")
                vals.append(int(bool(v)))
        if not cols:
            return self.get(user_id)
        vals.append(user_id)
        with self._lock, self._connect() as conn:
            conn.execute(
                f"UPDATE users SET {', '.join(cols)} WHERE user_id = %s",
                vals)
        return self.get(user_id)
