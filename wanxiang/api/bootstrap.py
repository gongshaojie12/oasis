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


def ensure_builtin_distributions(distribution_store) -> int:
    """M1:把内置 yaml 画像 seed 进 DB(幂等)。

    扫 ``wanxiang/datasources/distributions/*.yaml``,规范化后 upsert 为
    ``builtin=True`` 的画像。已存在的 builtin 画像**跳过**(不覆盖管理员
    可能做过的改动)。返回新 seed 的数量。

    Docker 里 distributions 目录只读,这里只**读**它作为 seed 源,数据落 DB。
    """
    import glob
    import hashlib
    import yaml as _yaml
    from datetime import datetime, timezone
    from wanxiang.api.distributions import (DistributionRecord, count_traits,
                                            slugify)
    from wanxiang.datasources.distribution import (load_distribution_from_dict,
                                                   validate_distribution)

    base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(
        __file__))), "datasources", "distributions")
    if not os.path.isdir(base):
        return 0
    seeded = 0
    # 支持 json / yaml / yml(json 优先与上传一致)。yaml.safe_load 也能解析 json,
    # 故统一用它解析,无需分支。
    paths = []
    for ext in ("*.json", "*.yaml", "*.yml"):
        paths.extend(glob.glob(os.path.join(base, ext)))
    for path in sorted(set(paths)):
        fname = os.path.basename(path)
        slug = slugify(fname.rsplit(".", 1)[0])
        if distribution_store.get_by_slug(slug) is not None:
            continue  # 已 seed 过,不覆盖
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = _yaml.safe_load(f) or {}
            ok, errs = validate_distribution(raw)
            if not ok:
                log.warning("Bootstrap: builtin dist %s invalid: %s",
                            fname, errs[:2])
                continue
            # 规范化(转 list 形态)后存 DB,与上传画像同构
            normalized = _normalize_for_storage(raw)
            # name 支持字符串或 {zh,en} 双语对象
            _nm = raw.get("name")
            if isinstance(_nm, dict):
                name_zh = _nm.get("zh") or _nm.get("en") or fname
                name_en = _nm.get("en") or name_zh
            elif isinstance(_nm, str):
                name_zh = name_en = _nm
            else:
                name_zh = name_en = fname
            did = "builtin_" + hashlib.md5(slug.encode()).hexdigest()[:12]
            now = datetime.now(timezone.utc)
            distribution_store.upsert(DistributionRecord(
                distribution_id=did, slug=slug, name_zh=name_zh,
                name_en=name_en, description="内置画像(系统预置)",
                source_type="builtin", content=normalized,
                trait_counts=count_traits(normalized),
                enabled=True, builtin=True,
                created_at=now, updated_at=now, created_by_user_id=None))
            seeded += 1
            log.info("Bootstrap: seeded builtin distribution %s", slug)
        except Exception as e:  # pragma: no cover (defensive)
            log.warning("Bootstrap: failed seeding %s: %s", fname, e)
    return seeded


def _normalize_for_storage(raw: dict) -> dict:
    """把 yaml(Plan A/B)转成统一的 Plan-B list 形态存库,便于前端编辑。"""
    from wanxiang.datasources.distribution import load_distribution_from_dict
    view = load_distribution_from_dict(raw)
    out: dict = {}
    if raw.get("name") is not None:
        out["name"] = raw["name"]  # str 或 {zh,en} 都原样保留
    for group in ("demographic", "personality", "media"):
        traits = []
        for trait in list(view.get(group, [])):
            traits.append({
                "name": trait["name"],
                "distribution": {"values": trait["distribution"]["values"]},
            })
        out[group] = traits
    return out


__all__ = ["ensure_demo_workspace_and_key", "ensure_super_admin",
           "ensure_builtin_distributions"]
