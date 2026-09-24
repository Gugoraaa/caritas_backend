from flask import Flask, jsonify
from flask_swagger_ui import get_swaggerui_blueprint

from .modules.app.controller import blueprint as app_blueprint
from .modules.auth.controller import blueprint as auth_blueprint
from .modules.causas.controller import blueprint as causas_blueprint
from .modules.donor.controller import blueprint as donors_blueprint
from .modules.historial.controller import blueprint as history_blueprint
from .modules.llamadas.controller import blueprint as calls_blueprint
from .openapi import build_spec

OPENAPI_JSON_URL = "/docs/openapi.json"


def register_routes(app: Flask) -> None:
    app.register_blueprint(app_blueprint)
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(calls_blueprint)
    app.register_blueprint(causas_blueprint)
    app.register_blueprint(donors_blueprint)
    app.register_blueprint(history_blueprint)

    app.add_url_rule(OPENAPI_JSON_URL, "openapi_spec", lambda: jsonify(build_spec()))
    app.register_blueprint(
        get_swaggerui_blueprint(
            "/docs", OPENAPI_JSON_URL, config={"app_name": "Caritas Backend API"}
        )
    )
