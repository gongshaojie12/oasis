"""Platform registry placeholder.

This module will be extended in Plan 3 to support custom platform
configurations beyond the built-in TWITTER and REDDIT types.
"""

from oasis.social_platform.typing import DefaultPlatformType

SUPPORTED_PLATFORMS = {
    "twitter": DefaultPlatformType.TWITTER,
    "reddit": DefaultPlatformType.REDDIT,
}


def resolve_platform(name: str) -> DefaultPlatformType:
    """Return the DefaultPlatformType for a platform name string."""
    platform = SUPPORTED_PLATFORMS.get(name.lower())
    if platform is None:
        available = ", ".join(sorted(SUPPORTED_PLATFORMS.keys()))
        raise ValueError(
            f"Unknown platform '{name}'. Available: {available}"
        )
    return platform
