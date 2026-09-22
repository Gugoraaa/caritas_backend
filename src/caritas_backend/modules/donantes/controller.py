from flask import Blueprint, Response, current_app, jsonify

blueprint = Blueprint("donantes", __name__)


@blueprint.get("/donantes")
def listar() -> Response:
    donantes = current_app.extensions["donantes"]
    return jsonify(donantes.list_donantes())
