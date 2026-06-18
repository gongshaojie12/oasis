from wanxiang.api.model_presets import MODEL_PRESETS, get_preset, mask_key


def test_presets_have_required_ids():
    ids = {p["id"] for p in MODEL_PRESETS}
    assert {"stub", "deepseek", "openai", "qwen", "custom"} <= ids


def test_each_preset_has_all_fields():
    for p in MODEL_PRESETS:
        assert set(p) == {"id", "label", "base_url", "default_model",
                          "needs_key", "allow_custom_base_url"}


def test_get_preset_found_and_missing():
    assert get_preset("deepseek")["default_model"] == "deepseek-chat"
    assert get_preset("nope") is None


def test_custom_allows_base_url_and_needs_key():
    c = get_preset("custom")
    assert c["allow_custom_base_url"] is True
    assert c["needs_key"] is True
    assert c["base_url"] is None


def test_stub_needs_no_key():
    assert get_preset("stub")["needs_key"] is False


def test_mask_key():
    assert mask_key("sk-abcdef1234") == "sk-…1234"
    assert mask_key("") is None
    assert mask_key(None) is None
    assert mask_key("ab") == "…ab"
