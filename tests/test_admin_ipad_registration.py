from flask import Flask

from caritas_backend.openapi import build_spec
from caritas_backend.routes import register_routes


def test_admin_ipad_routes_and_documentation():
    app = Flask(__name__)
    register_routes(app)
    spec = build_spec()

    for path in ("/admin/summary", "/admin/calls", "/admin/users"):
        assert any(
            rule.rule == path and "GET" in rule.methods
            for rule in app.url_map.iter_rules()
        )
        assert spec["paths"][path]["get"]["security"] == [{"bearerAuth": []}]
        assert "200" in spec["paths"][path]["get"]["responses"]
