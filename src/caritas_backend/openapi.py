from apispec import APISpec
from apispec_webframeworks.flask import FlaskPlugin
from flask import Flask, jsonify
from flask_swagger_ui import get_swaggerui_blueprint

SWAGGER_URL = "/docs"
SPEC_URL = "/openapi.json"

ERROR_RESPONSE = {
    "type": "object",
    "properties": {
        "message": {"oneOf": [{"type": "string"}, {"type": "array"}]},
        "error": {"type": "string"},
        "statusCode": {"type": "integer"},
    },
}


def build_spec(app: Flask) -> dict:
    spec = APISpec(
        title="Caritas Backend API",
        version="1.0.0",
        openapi_version="3.0.3",
        plugins=[FlaskPlugin()],
        info={
            "description": (
                "API del backend de Caritas: gestion de donantes, historial de "
                "donativos/llamadas, llamadas agendadas y autenticacion."
            )
        },
    )
    spec.components.schema("Error", ERROR_RESPONSE)

    with app.test_request_context():
        for rule in app.url_map.iter_rules():
            if rule.endpoint == "static":
                continue
            view = app.view_functions[rule.endpoint]
            if view.__doc__ and "---" in view.__doc__:
                spec.path(view=view)

    return spec.to_dict()


def register_docs(app: Flask) -> None:
    @app.get(SPEC_URL)
    def openapi_spec():
        return jsonify(build_spec(app))

    swagger_blueprint = get_swaggerui_blueprint(
        SWAGGER_URL, SPEC_URL, config={"app_name": "Caritas Backend API"}
    )
    app.register_blueprint(swagger_blueprint, url_prefix=SWAGGER_URL)
