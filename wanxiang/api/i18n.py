# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""i18n message catalog + locale resolution helpers.

Catalogs use kebab-case keys grouped by domain. Adding a new message =
add one key with {zh, en} values. Missing translation falls back to zh.
Missing key returns the raw key (helps spotting untranslated calls).

Locale resolution priority (highest first):
1. explicit lang parameter on t()
2. request.state.locale (set by RequestLocaleMiddleware)
3. fallback "zh"
"""
from __future__ import annotations

from typing import Literal

Locale = Literal["zh", "en"]
SUPPORTED_LOCALES: tuple[Locale, ...] = ("zh", "en")
DEFAULT_LOCALE: Locale = "zh"

CATALOG: dict[str, dict[Locale, str]] = {
    # auth
    "auth.missing_api_key": {
        "zh": "缺少 X-API-Key 请求头",
        "en": "Missing X-API-Key header",
    },
    "auth.invalid_api_key": {
        "zh": "无效的 API Key",
        "en": "Invalid API key",
    },
    "auth.rate_limit_exceeded": {
        "zh": "请求过于频繁，请稍后再试（租户 {tenant_id}）",
        "en": "Rate limit exceeded for tenant {tenant_id}, please retry later",
    },
    "auth.budget_exhausted": {
        "zh": "本月预算已耗尽",
        "en": "Monthly budget exhausted",
    },
    # validation
    "request.invalid_locale": {
        "zh": "不支持的 locale: {locale}（仅支持 zh/en）",
        "en": "Unsupported locale: {locale} (only zh/en allowed)",
    },
    "request.task_not_found": {
        "zh": "任务不存在",
        "en": "Task not found",
    },
    "request.template_not_found": {
        "zh": "模板不存在: {template_id}",
        "en": "Template not found: {template_id}",
    },
    "request.template_instantiate_failed": {
        "zh": "模板实例化失败: {error}",
        "en": "Template instantiation failed: {error}",
    },
    "request.invalid_usage_query": {
        "zh": "无效的用量查询参数: {error}",
        "en": "Invalid usage query parameter: {error}",
    },
    # simulation
    "sim.distribution_file_not_found": {
        "zh": "分布文件不存在: {path}",
        "en": "Distribution file not found: {path}",
    },
    "sim.material_flagged_by_moderator": {
        "zh": "材料被审核器标记为不安全: {reason}",
        "en": "Material flagged by moderator as unsafe: {reason}",
    },
    "sim.unknown_platform": {
        "zh": "未知平台: {platform}",
        "en": "Unknown platform: {platform}",
    },
    "sim.sweep_too_many_combos": {
        "zh": "组合数 {n} 超出上限 {limit}",
        "en": "Sweep would produce {n} combos, exceeds limit of {limit}",
    },
    # report
    "report.bad_request_xor": {
        "zh": "必须且只能提供一个: markdown 或 task_id",
        "en": "Provide exactly one of: markdown | task_id",
    },
    "report.task_not_done": {
        "zh": "任务状态为 {status}，未完成",
        "en": "Task status is {status}, not done",
    },
    "report.task_has_no_markdown": {
        "zh": "任务没有 markdown 报告",
        "en": "Task has no markdown report",
    },
    "report.pdf_unavailable": {
        "zh": "PDF 导出未启用: {reason}",
        "en": "PDF export unavailable: {reason}",
    },
    # audit
    "audit.invalid_iso_datetime": {
        "zh": "无效的 ISO 8601 时间: {value}",
        "en": "Invalid ISO 8601 datetime: {value}",
    },
    # P1: user auth (JWT path; X-API-Key catalog above still applies to legacy)
    "auth.email_or_phone_required": {
        "zh": "必须提供邮箱或手机号",
        "en": "Email or phone required",
    },
    "auth.invalid_phone_format": {
        "zh": "手机号格式无效",
        "en": "Invalid phone number format",
    },
    "auth.password_too_short": {
        "zh": "密码至少 8 位",
        "en": "Password must be at least 8 characters",
    },
    "auth.password_too_weak": {
        "zh": "密码需包含字母和数字",
        "en": "Password must contain letters and digits",
    },
    "auth.email_already_registered": {
        "zh": "该邮箱已注册",
        "en": "Email already registered",
    },
    "auth.phone_already_registered": {
        "zh": "该手机号已注册",
        "en": "Phone already registered",
    },
    "auth.invalid_credentials": {
        "zh": "用户名或密码错误",
        "en": "Invalid username or password",
    },
    "auth.missing_token": {
        "zh": "缺少认证 token",
        "en": "Missing auth token",
    },
    "auth.invalid_token": {
        "zh": "token 无效或已过期",
        "en": "Invalid or expired token",
    },
    "auth.user_not_found": {
        "zh": "用户不存在",
        "en": "User not found",
    },
    # P3: workspace + invite + api-key
    "workspace.not_found": {
        "zh": "Workspace 不存在",
        "en": "Workspace not found",
    },
    "workspace.not_a_member": {
        "zh": "不是该 Workspace 成员",
        "en": "Not a member of this workspace",
    },
    "workspace.requires_admin": {
        "zh": "需要管理员权限",
        "en": "Admin role required",
    },
    "workspace.requires_owner": {
        "zh": "需要 Owner 权限",
        "en": "Owner role required",
    },
    "workspace.cannot_delete_personal": {
        "zh": "个人 Workspace 不可删除",
        "en": "Personal workspace cannot be deleted",
    },
    "workspace.cannot_remove_owner": {
        "zh": "不能移除 Owner",
        "en": "Cannot remove owner",
    },
    "workspace.member_not_found": {
        "zh": "成员不存在",
        "en": "Member not found",
    },
    "workspace.slug_taken": {
        "zh": "Slug 已被占用",
        "en": "Slug already taken",
    },
    "workspace.invite_invalid_or_expired": {
        "zh": "邀请无效或已过期",
        "en": "Invite invalid or expired",
    },
    "workspace.invite_already_accepted": {
        "zh": "邀请已被接受",
        "en": "Invite already accepted",
    },
    "workspace.invite_email_mismatch": {
        "zh": "邀请邮箱与当前账号不一致",
        "en": "Invite email does not match current account",
    },
    "workspace.api_key_not_found": {
        "zh": "API Key 不存在",
        "en": "API key not found",
    },
    # P2: verification code flow
    "auth.invalid_email_format": {
        "zh": "邮箱格式无效",
        "en": "Invalid email format",
    },
    "auth.verification_rate_limit": {
        "zh": "验证码请求过于频繁（{n} 条/小时上限）",
        "en": "Verification rate limit reached ({n} per hour)",
    },
    "auth.no_active_code": {
        "zh": "无可用验证码，请先获取",
        "en": "No active code. Request one first",
    },
    "auth.too_many_attempts": {
        "zh": "验证次数超限，请重新获取验证码",
        "en": "Too many attempts. Request a new code",
    },
    "auth.invalid_code": {
        "zh": "验证码错误，剩余 {remaining} 次",
        "en": "Invalid code, {remaining} attempts remaining",
    },
}


def t(key: str, *, locale: Locale | None = None, **kwargs) -> str:
    """Translate a catalog key. ``kwargs`` are formatted into the template.

    Missing key -> returns the key verbatim (visible in tests).
    Missing locale value -> falls back to zh.
    """
    loc: Locale = locale or DEFAULT_LOCALE
    entry = CATALOG.get(key)
    if entry is None:
        return key
    template = entry.get(loc) or entry.get(DEFAULT_LOCALE) or key
    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError):
            return template
    return template


def normalize_locale(raw: str | None) -> Locale | None:
    """Map flexible inputs to canonical Locale: 'zh-CN' -> 'zh', 'en-US' -> 'en'."""
    if not raw:
        return None
    s = raw.strip().lower()
    if not s:
        return None
    # Take just the language portion before '-' or '_' or ','
    head = s.replace("_", "-").split(",")[0].strip().split("-")[0]
    if head == "zh":
        return "zh"
    if head == "en":
        return "en"
    return None


def parse_accept_language(header: str | None) -> Locale | None:
    """Naive Accept-Language parser: pick first supported tag (ignore q-weights).

    Examples:
      "en"           -> "en"
      "en-US"        -> "en"
      "zh-CN,en;q=0.5" -> "zh"
      "fr"           -> None
    """
    if not header:
        return None
    for raw in header.split(","):
        loc = normalize_locale(raw.split(";")[0])
        if loc is not None:
            return loc
    return None


def get_request_locale(request) -> Locale:
    """Pull locale from request.state, fallback to DEFAULT_LOCALE."""
    return getattr(request.state, "locale", None) or DEFAULT_LOCALE


__all__ = [
    "Locale", "SUPPORTED_LOCALES", "DEFAULT_LOCALE", "CATALOG",
    "t", "normalize_locale", "parse_accept_language", "get_request_locale",
]
