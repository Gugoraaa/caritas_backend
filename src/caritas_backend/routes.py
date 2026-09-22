
from flask import Flask

from .modules.app.controller import blueprint as app_blueprint
from .modules.auth.controller import blueprint as auth_blueprint
from .modules.llamadas.controller import blueprint as calls_blueprint


def register_routes(app: Flask) -> None:
    app.register_blueprint(app_blueprint)
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(calls_blueprint)
