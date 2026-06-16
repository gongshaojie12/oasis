# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""P1: SqliteUserStore persistence tests."""
from __future__ import annotations

import os

import pytest

from wanxiang.api.users import User, hash_password, make_user_store


def _mk_user(email=None, phone=None, name="X"):
    return User(user_id="auto", email=email, phone=phone,
                 password_hash=hash_password("Hello123!"), display_name=name)


def test_sqlite_create_get_roundtrip(tmp_path):
    db = str(tmp_path / "users.db")
    store = make_user_store(db)
    u = store.create(_mk_user(email="a@b.com", name="Alice"))
    assert u.user_id
    got = store.get(u.user_id)
    assert got is not None
    assert got.email == "a@b.com"
    assert got.display_name == "Alice"


def test_sqlite_persistence_across_reopen(tmp_path):
    db = str(tmp_path / "users.db")
    s1 = make_user_store(db)
    u = s1.create(_mk_user(email="persist@x.com", name="P"))
    uid = u.user_id
    # reopen
    s2 = make_user_store(db)
    got = s2.get(uid)
    assert got is not None and got.email == "persist@x.com"


def test_sqlite_email_lookup(tmp_path):
    db = str(tmp_path / "users.db")
    store = make_user_store(db)
    store.create(_mk_user(email="lookup@x.com", name="L"))
    got = store.get_by_email("LOOKUP@X.com")
    assert got is not None and got.display_name == "L"


def test_sqlite_phone_lookup(tmp_path):
    db = str(tmp_path / "users.db")
    store = make_user_store(db)
    store.create(_mk_user(phone="13800138000", name="P"))
    got = store.get_by_phone("13800138000")
    assert got is not None and got.display_name == "P"


def test_sqlite_duplicate_email_constraint(tmp_path):
    db = str(tmp_path / "users.db")
    store = make_user_store(db)
    store.create(_mk_user(email="dup@x.com", name="D1"))
    with pytest.raises(Exception):
        store.create(_mk_user(email="dup@x.com", name="D2"))


def test_sqlite_nullable_email_phone(tmp_path):
    """Two users with NULL email/phone should coexist (partial unique index)."""
    db = str(tmp_path / "users.db")
    store = make_user_store(db)
    u1 = store.create(_mk_user(email="only@x.com", phone=None, name="E"))
    u2 = store.create(_mk_user(email=None, phone="13800138001", name="P"))
    assert u1.user_id != u2.user_id
    # A third with both NULL also OK
    u3 = store.create(User(user_id="auto", email=None, phone=None,
                            password_hash=hash_password("Hello123!"),
                            display_name="N"))
    assert u3.user_id
