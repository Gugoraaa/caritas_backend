from flask import Blueprint, Response, current_app, jsonify, request

from ...errors import HttpException

blueprint = Blueprint("llamadas", __name__)


@blueprint.get("/llamadas/agendadas")
def agendadas_hoy_manana() -> Response:
    user_id = _parse_user_id()
    llamadas = current_app.extensions["llamadas"]
    return jsonify(llamadas.agendadas_hoy_manana(user_id))


def _parse_user_id() -> int:
    raw = request.args.get("user_id")
    if not raw or not raw.isdigit():
        raise HttpException(400, "user_id debe ser un entero")
    return int(raw)
