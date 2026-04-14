"""Tests for PlatformRegistry."""

import os
import os.path as osp

import pytest

from oasis.social_platform.platform import Platform
from oasis.social_platform.typing import RecsysType

from engine.platforms import PlatformConfig, PlatformRegistry, registry

parent_folder = osp.dirname(osp.abspath(__file__))
test_db_filepath = osp.join(parent_folder, "test_registry.db")


class TestPlatformConfig:
    def test_default_values(self):
        config = PlatformConfig(
            name="test",
            adapter_class=Platform,
        )
        assert config.name == "test"
        assert config.default_recsys == "random"
        assert config.default_actions == []
        assert config.description == ""
        assert config.language == "zh-CN"


class TestPlatformRegistry:
    def setup_method(self):
        self.registry = PlatformRegistry()

    def test_register_and_get(self):
        self.registry.register(
            name="test_platform",
            adapter_class=Platform,
            default_recsys="random",
            description="A test platform",
        )
        config = self.registry.get("test_platform")
        assert config.name == "test_platform"
        assert config.adapter_class is Platform
        assert config.default_recsys == "random"

    def test_register_duplicate_raises(self):
        self.registry.register("dup", Platform)
        with pytest.raises(ValueError, match="already registered"):
            self.registry.register("dup", Platform)

    def test_get_missing_raises(self):
        with pytest.raises(KeyError, match="not registered"):
            self.registry.get("nonexistent")

    def test_unregister(self):
        self.registry.register("removable", Platform)
        assert "removable" in self.registry.list_platforms()
        self.registry.unregister("removable")
        assert "removable" not in self.registry.list_platforms()

    def test_unregister_missing_raises(self):
        with pytest.raises(KeyError, match="not registered"):
            self.registry.unregister("ghost")

    def test_list_platforms_sorted(self):
        self.registry.register("charlie", Platform)
        self.registry.register("alpha", Platform)
        self.registry.register("bravo", Platform)
        assert self.registry.list_platforms() == [
            "alpha", "bravo", "charlie"
        ]

    def test_create_platform(self):
        self.registry.register(
            "factory_test",
            Platform,
            default_recsys="random",
        )
        try:
            platform = self.registry.create_platform(
                "factory_test",
                db_path=test_db_filepath,
            )
            assert isinstance(platform, Platform)
            assert platform.recsys_type == RecsysType.RANDOM
        finally:
            platform.db_cursor.close()
            platform.db.close()
            if os.path.exists(test_db_filepath):
                os.remove(test_db_filepath)

    def test_create_platform_missing_raises(self):
        with pytest.raises(KeyError, match="not registered"):
            self.registry.create_platform("missing", db_path=":memory:")


class TestGlobalRegistry:
    def test_builtin_twitter_registered(self):
        assert "twitter" in registry.list_platforms()
        config = registry.get("twitter")
        assert config.adapter_class is Platform
        assert config.default_recsys == "twitter"

    def test_builtin_reddit_registered(self):
        assert "reddit" in registry.list_platforms()
        config = registry.get("reddit")
        assert config.adapter_class is Platform
        assert config.default_recsys == "reddit"
