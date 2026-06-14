# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""Content moderation protocol (M3-12).

Defines a pluggable interface. Default = NoOpModerator (everything passes).
Production deployment can swap in OpenAI/Anthropic/Aliyun/Tencent moderation.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class ModerationVerdict(str, Enum):
    SAFE = "safe"
    UNSAFE = "unsafe"
    REVIEW = "review"


@dataclass(frozen=True)
class ModerationResult:
    verdict: ModerationVerdict
    categories: tuple[str, ...] = ()   # e.g. ("hate", "self_harm")
    raw: dict | None = None             # provider-specific raw response


class ModeratorProtocol(Protocol):
    async def check(self, text: str) -> ModerationResult: ...


class NoOpModerator:
    """Always returns SAFE. Default for development; production should swap."""
    async def check(self, text: str) -> ModerationResult:
        return ModerationResult(verdict=ModerationVerdict.SAFE)


class KeywordBlocklistModerator:
    """Local fallback: flag if text contains any blocklist word. Minimal."""
    def __init__(self, blocklist: list[str]):
        self.blocklist = [w.lower() for w in blocklist]

    async def check(self, text: str) -> ModerationResult:
        low = (text or "").lower()
        hits = [w for w in self.blocklist if w in low]
        if hits:
            return ModerationResult(
                verdict=ModerationVerdict.UNSAFE,
                categories=tuple(hits))
        return ModerationResult(verdict=ModerationVerdict.SAFE)
