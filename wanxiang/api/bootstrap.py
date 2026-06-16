# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""On startup: ensure 'demo' workspace + 'demo-key' API key exist (P3).

Idempotent — safe to run on every boot. Reads:
  * ``WANXIANG_DEFAULT_API_KEY`` (default ``"demo-key"``)
  * ``WANXIANG_DEFAULT_WORKSPACE_SLUG`` (default ``"demo"``)

Migration from legacy ``WANXIANG_TENANTS_JSON``: if set and not already
migrated, parse each entry and create matching workspace + api_key row.
"""
from __future__ import annotations

import json
import logging
import os

log = logging.getLogger(__name__)


def ensure_demo_workspace_and_key(*, user_store, workspace_store,
                                    api_key_store):
    """Idempotent. Returns ``(workspace, api_key)`` for the default tenant."""
    from wanxiang.api.api_keys import ApiKey
    from wanxiang.api.users import User, hash_password
    from wanxiang.api.workspaces import Workspace, WorkspaceMember

    default_key = os.environ.get("WANXIANG_DEFAULT_API_KEY", "demo-key")
    default_slug = os.environ.get("WANXIANG_DEFAULT_WORKSPACE_SLUG", "demo")

    # Already provisioned?
    existing = api_key_store.lookup(default_key)
    if existing:
        ws = workspace_store.get_workspace(existing.workspace_id)
        # Still attempt legacy import (idempotent — checked per-key below)
        _seed_legacy_tenants(workspace_store, api_key_store, user_store,
                              fallback_owner_email="demo@wanxiang.local")
        return ws, existing

    # Ensure the demo user exists (system user that owns the demo workspace)
    demo_user = user_store.get_by_email("demo@wanxiang.local")
    if not demo_user:
        demo_user = User(
            user_id="auto", email="demo@wanxiang.local", phone=None,
            password_hash=hash_password("demo-only-not-for-prod-XYZ123"),
            display_name="Demo User", locale="zh",
            email_verified=True, is_super_admin=False,
        )
        demo_user = user_store.create(demo_user)

    # Ensure the demo workspace exists
    ws = workspace_store.get_by_slug(default_slug)
    if not ws:
        ws = Workspace(
            workspace_id="auto", slug=default_slug,
            name="Demo Workspace", type="personal",
            owner_user_id=demo_user.user_id, locale="zh",
            balance_cost_units=100_000,
        )
        ws = workspace_store.create_workspace(ws)
        workspace_store.add_member(WorkspaceMember(
            workspace_id=ws.workspace_id, user_id=demo_user.user_id,
            role="owner"))

    # Create the default api key
    ak = ApiKey(
        key_id="auto", workspace_id=ws.workspace_id,
        api_key=default_key, name="Default Demo Key",
        role="admin", rpm_limit=60,
    )
    ak = api_key_store.create(ak)
    log.info("Bootstrap: created demo workspace=%s with api_key=%s",
             ws.slug, default_key)

    _seed_legacy_tenants(workspace_store, api_key_store, user_store,
                          fallback_owner_email="demo@wanxiang.local")
    return ws, ak


def ensure_super_admin(*, user_store) -> bool:
    """P4: ensure a super-admin user exists when ``WANXIANG_SUPER_ADMIN_EMAIL``
    (and ``WANXIANG_SUPER_ADMIN_PASSWORD``) env vars are set.

    Idempotent: if a user with the given email already exists, just flip
    ``is_super_admin=True`` (don't reset the password). Returns True if
    a user was created or modified.

    No-op when ``WANXIANG_SUPER_ADMIN_EMAIL`` is unset — per spec we don't
    want to silently provision a super-admin with a random password.
    """
    from wanxiang.api.users import User, hash_password

    email = os.environ.get("WANXIANG_SUPER_ADMIN_EMAIL")
    if not email:
        return False
    password = os.environ.get("WANXIANG_SUPER_ADMIN_PASSWORD")
    if not password:
        log.warning("Bootstrap: WANXIANG_SUPER_ADMIN_EMAIL set without "
                     "WANXIANG_SUPER_ADMIN_PASSWORD — skipping super-admin")
        return False

    existing = user_store.get_by_email(email)
    if existing:
        if not existing.is_super_admin:
            user_store.update(existing.user_id, is_super_admin=True)
            log.info("Bootstrap: promoted existing user %s to super-admin",
                      email)
            return True
        return False

    user = User(
        user_id="auto", email=email, phone=None,
        password_hash=hash_password(password),
        display_name=email.split("@")[0],
        locale="zh", email_verified=True, is_super_admin=True,
    )
    user_store.create(user)
    log.info("Bootstrap: created super-admin %s", email)
    return True


def _seed_legacy_tenants(workspace_store, api_key_store, user_store, *,
                          fallback_owner_email: str) -> None:
    """Migrate legacy ``WANXIANG_TENANTS_JSON`` entries as workspace + api_key."""
    from wanxiang.api.api_keys import ApiKey
    from wanxiang.api.workspaces import Workspace, WorkspaceMember

    legacy = os.environ.get("WANXIANG_TENANTS_JSON")
    if not legacy:
        return
    try:
        tenants = json.loads(legacy)
    except (json.JSONDecodeError, ValueError) as e:
        log.warning("Bootstrap: failed to parse WANXIANG_TENANTS_JSON: %s", e)
        return
    owner = user_store.get_by_email(fallback_owner_email)
    if not owner:
        # Nothing sensible to attribute these to — skip
        log.warning(
            "Bootstrap: legacy tenants requested but no demo user available")
        return
    for entry in tenants:
        try:
            key = entry.get("api_key")
            if not key or api_key_store.lookup(key):
                continue
            slug = entry.get("tenant_id") or ("legacy-" + key[:6])
            ws = workspace_store.get_by_slug(slug)
            if not ws:
                ws = Workspace(
                    workspace_id="auto", slug=slug, name=slug,
                    type="personal", owner_user_id=owner.user_id,
                    locale=entry.get("default_locale", "zh"),
                    balance_cost_units=0,
                )
                ws = workspace_store.create_workspace(ws)
                workspace_store.add_member(WorkspaceMember(
                    workspace_id=ws.workspace_id, user_id=owner.user_id,
                    role="owner"))
            ak = ApiKey(
                key_id="auto", workspace_id=ws.workspace_id,
                api_key=key, name=f"Legacy: {slug}",
                role="member",
                rpm_limit=int(entry.get("rpm_limit", 60)),
                monthly_budget=entry.get("monthly_budget"),
            )
            api_key_store.create(ak)
            log.info("Bootstrap legacy: migrated tenant=%s key=%s", slug, key)
        except (KeyError, ValueError, TypeError) as e:
            log.warning("Bootstrap: skipping legacy entry %r: %s", entry, e)


__all__ = ["ensure_demo_workspace_and_key", "ensure_super_admin"]
