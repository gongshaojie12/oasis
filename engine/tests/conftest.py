import os

import pytest


@pytest.fixture(autouse=True)
def reset_settings_cache():
    """Clear the lru_cache on get_settings between tests."""
    from engine.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
