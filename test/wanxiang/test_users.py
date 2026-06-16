# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""P1: User model + InMemoryUserStore unit tests."""
from __future__ import annotations

import pytest

from wanxiang.api.users import (
    InMemoryUserStore,
    User,
    hash_password,
    validate_password,
    verify_password,
)


def test_password_hash_verify_roundtrip():
    raw = "Hello123!"
    h = hash_password(raw)
    assert h and h != raw
    assert verify_password(raw, h) is True


def test_verify_rejects_wrong_password():
    h = hash_password("Hello123!")
    assert verify_password("WrongPass1", h) is False


def test_verify_rejects_corrupt_hash():
    assert verify_password("anything", "not-a-bcrypt-hash") is False


def test_validate_password_too_short():
    assert validate_password("abc12") == "auth.password_too_short"


def test_validate_password_no_digit():
    assert validate_password("abcdefgh") == "auth.password_too_weak"


def test_validate_password_no_letter():
    assert validate_password("12345678") == "auth.password_too_weak"


def test_validate_password_ok():
    assert validate_password("Hello123!") is None


def test_store_create_get_by_email():
    store = InMemoryUserStore()
    u = User(user_id="auto", email="a@b.com", phone=None,
             password_hash=hash_password("Hello123!"), display_name="A")
    saved = store.create(u)
    assert saved.user_id and saved.user_id != "auto"
    got = store.get_by_email("A@B.com")  # case-insensitive
    assert got is not None and got.user_id == saved.user_id


def test_store_create_get_by_phone():
    store = InMemoryUserStore()
    u = User(user_id="auto", email=None, phone="13800138000",
             password_hash=hash_password("Hello123!"), display_name="P")
    store.create(u)
    got = store.get_by_phone("13800138000")
    assert got is not None and got.display_name == "P"


def test_store_duplicate_email_raises():
    store = InMemoryUserStore()
    store.create(User(user_id="auto", email="dup@x.com", phone=None,
                       password_hash="x", display_name="D1"))
    with pytest.raises(ValueError):
        store.create(User(user_id="auto", email="dup@x.com", phone=None,
                           password_hash="x", display_name="D2"))


def test_store_duplicate_phone_raises():
    store = InMemoryUserStore()
    store.create(User(user_id="auto", email=None, phone="13800138000",
                       password_hash="x", display_name="P1"))
    with pytest.raises(ValueError):
        store.create(User(user_id="auto", email=None, phone="13800138000",
                           password_hash="x", display_name="P2"))


def test_user_to_safe_dict_omits_password_hash():
    u = User(user_id="u1", email="a@b.com", phone=None,
             password_hash="SECRET", display_name="A")
    d = u.to_safe_dict()
    assert "password_hash" not in d
    assert d["user_id"] == "u1"
    assert d["email"] == "a@b.com"
