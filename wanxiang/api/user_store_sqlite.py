# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""SqliteUserStore (P1) — mirrors SqliteUsageStore pattern."""
from __future__ import annotations

import os
import sqlite3
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


def _row_to_user(row: sqlite3.Row) -> User:
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


class SqliteUserStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        parent = os.path.dirname(os.path.abspath(db_path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        self._lock = Lock()
        with self._connect() as conn:
            conn.executescript(_SCHEMA)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False,
                                isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def create(self, user: User) -> User:
        if user.user_id == "auto":
            user.user_id = uuid.uuid4().hex
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO users "
                "(user_id, email, phone, password_hash, display_name, "
                " locale, avatar_url, email_verified, phone_verified, "
                " is_super_admin, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (user.user_id, user.email, user.phone, user.password_hash,
                 user.display_name, user.locale, user.avatar_url,
                 int(user.email_verified), int(user.phone_verified),
                 int(user.is_super_admin), user.created_at.isoformat()))
        return user

    def get(self, user_id: str) -> User | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE user_id = ?",
                (user_id,)).fetchone()
        return _row_to_user(row) if row else None

    def get_by_email(self, email: str) -> User | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE LOWER(email) = LOWER(?)",
                (email,)).fetchone()
        return _row_to_user(row) if row else None

    def get_by_phone(self, phone: str) -> User | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE phone = ?",
                (phone,)).fetchone()
        return _row_to_user(row) if row else None

    def update(self, user_id: str, **fields) -> User | None:
        if not fields:
            return self.get(user_id)
        cols: list[str] = []
        vals: list = []
        for k, v in fields.items():
            if k in ("email", "phone", "password_hash", "display_name",
                     "locale", "avatar_url"):
                cols.append(f"{k} = ?")
                vals.append(v)
            elif k in ("email_verified", "phone_verified", "is_super_admin"):
                cols.append(f"{k} = ?")
                vals.append(int(bool(v)))
        if not cols:
            return self.get(user_id)
        vals.append(user_id)
        with self._lock, self._connect() as conn:
            conn.execute(
                f"UPDATE users SET {', '.join(cols)} WHERE user_id = ?",
                vals)
        return self.get(user_id)

    def list_all(self, *, limit: int = 100) -> list[User]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM users ORDER BY created_at DESC LIMIT ?",
                (int(limit),)).fetchall()
        return [_row_to_user(r) for r in rows]
