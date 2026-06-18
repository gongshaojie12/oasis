from wanxiang.api.app import create_app


def test_app_has_model_config_store():
    app = create_app()
    assert hasattr(app.state, "model_config_store")
    assert app.state.model_config_store.get("nope") is None
