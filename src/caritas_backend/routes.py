from flask import Flask, jsonify
from flask_swagger_ui import get_swaggerui_blueprint

from .modules.admin.controller import blueprint as admin_blueprint
from .modules.admin_llamadas.controller import blueprint as admin_calls_blueprint
from .modules.admin_resumen.controller import blueprint as admin_resumen_blueprint
from .modules.admin_usuarios.controller import blueprint as admin_users_blueprint
from .modules.app.controller import blueprint as app_blueprint
from .modules.auth.controller import blueprint as auth_blueprint
from .modules.causas.controller import blueprint as causas_blueprint
from .modules.donor.controller import blueprint as donors_blueprint
from .modules.health.controller import blueprint as health_blueprint
from .modules.historial.controller import blueprint as history_blueprint
from .modules.llamadas.controller import blueprint as calls_blueprint
from .modules.recolecciones.controller import blueprint as collections_blueprint
from .modules.seed.controller import blueprint as seed_blueprint
from .openapi import build_spec

OPENAPI_JSON_URL = "/docs/openapi.json"


def register_routes(app: Flask) -> None:
    app.register_blueprint(app_blueprint)
    app.register_blueprint(admin_blueprint)
    app.register_blueprint(admin_calls_blueprint)
    app.register_blueprint(admin_resumen_blueprint)
    app.register_blueprint(admin_users_blueprint)
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(calls_blueprint)
    app.register_blueprint(causas_blueprint)
    app.register_blueprint(donors_blueprint)
    app.register_blueprint(history_blueprint)
    app.register_blueprint(collections_blueprint)
    app.register_blueprint(health_blueprint)
    app.register_blueprint(seed_blueprint)

    app.add_url_rule(OPENAPI_JSON_URL, "openapi_spec", lambda: jsonify(build_spec()))
    app.register_blueprint(
        get_swaggerui_blueprint(
            "/docs", OPENAPI_JSON_URL, config={"app_name": "Caritas Backend API"}
        )
    )
