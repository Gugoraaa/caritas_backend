from flask import Flask, jsonify

from caritas_backend.errors import register_error_handlers
from caritas_backend.rate_limit import (
    RateLimiter,
    rate_limited,
    register_rate_limit,
)
from caritas_backend.secure_headers import API_CSP, DOCS_CSP, register_secure_headers


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def make_app(monkeypatch, rate="100/1m", login_rate="2/1m"):
    monkeypatch.setenv("RATE_LIMIT", rate)
    monkeypatch.setenv("LOGIN_RATE_LIMIT", login_rate)
    app = Flask(__name__)
    register_error_handlers(app)
    register_rate_limit(app)
    register_secure_headers(app)

    @app.post("/login")
    @rate_limited("login_limiter")
    def login():
        return jsonify(ok=True)

    @app.get("/docs/")
    def docs():
        return "docs"

    return app.test_client()


def test_limiter_blocks_after_limit_and_reopens_after_window():
    clock = FakeClock()
    limiter = RateLimiter(2, 60, clock=clock)
    assert limiter.hit("ip") is None
    assert limiter.hit("ip") is None
    assert limiter.hit("ip") == 60

    clock.now = 30
    assert limiter.hit("ip") == 30
    assert limiter.hit("otra-ip") is None

    clock.now = 60
    assert limiter.hit("ip") is None


def test_login_returns_429_with_retry_after(monkeypatch):
    client = make_app(monkeypatch)
    assert client.post("/login").status_code == 200
    assert client.post("/login").status_code == 200

    response = client.post("/login")
    assert response.status_code == 429
    assert response.json["statusCode"] == 429
    assert int(response.headers["Retry-After"]) >= 1


def test_global_limit_applies_to_every_route(monkeypatch):
    client = make_app(monkeypatch, rate="1/1m")
    assert client.get("/nada").status_code == 404
    assert client.get("/nada").status_code == 429


def test_secure_headers_on_api_and_errors(monkeypatch):
    client = make_app(monkeypatch)
    response = client.get("/nada")
    assert response.status_code == 404
    assert response.headers["Content-Security-Policy"] == API_CSP
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "max-age=" in response.headers["Strict-Transport-Security"]
    assert response.headers["Cross-Origin-Embedder-Policy"] == "require-corp"
    assert "no-store" in response.headers["Cache-Control"]
    assert "form-action 'none'" in response.headers["Content-Security-Policy"]


def test_docs_get_relaxed_csp(monkeypatch):
    client = make_app(monkeypatch)
    assert client.get("/docs/").headers["Content-Security-Policy"] == DOCS_CSP
