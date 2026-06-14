# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""RequestLocaleMiddleware: priority body > header > tenant > default."""
import json

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from wanxiang.api.locale_middleware import RequestLocaleMiddleware


def _mk_app():
    app = FastAPI()
    app.add_middleware(RequestLocaleMiddleware)

    @app.post("/echo")
    async def echo(request: Request):
        return {"locale": request.state.locale}

    @app.get("/get_echo")
    async def get_echo(request: Request):
        return {"locale": request.state.locale}

    return app


def test_default_locale_is_zh():
    c = TestClient(_mk_app())
    r = c.get("/get_echo")
    assert r.json()["locale"] == "zh"


def test_accept_language_en():
    c = TestClient(_mk_app())
    r = c.get("/get_echo", headers={"accept-language": "en"})
    assert r.json()["locale"] == "en"


def test_accept_language_en_us():
    c = TestClient(_mk_app())
    r = c.get("/get_echo", headers={"accept-language": "en-US"})
    assert r.json()["locale"] == "en"


def test_accept_language_unsupported_fallback():
    c = TestClient(_mk_app())
    r = c.get("/get_echo", headers={"accept-language": "fr"})
    assert r.json()["locale"] == "zh"


def test_body_locale_overrides_header():
    c = TestClient(_mk_app())
    r = c.post("/echo", json={"locale":"en"},
               headers={"accept-language":"zh"})
    assert r.json()["locale"] == "en"


def test_body_invalid_locale_falls_back_to_header():
    c = TestClient(_mk_app())
    r = c.post("/echo", json={"locale":"fr"},
               headers={"accept-language":"en"})
    assert r.json()["locale"] == "en"


def test_body_no_locale_field_uses_header():
    c = TestClient(_mk_app())
    r = c.post("/echo", json={"other":"data"},
               headers={"accept-language":"en"})
    assert r.json()["locale"] == "en"


def test_skip_paths_use_default():
    app = _mk_app()
    @app.get("/healthz")
    async def h(request: Request):
        return {"locale": getattr(request.state, "locale", "zh")}
    c = TestClient(app)
    r = c.get("/healthz", headers={"accept-language":"en"})
    # Middleware skips /healthz → defaults to zh
    assert r.json()["locale"] == "zh"
