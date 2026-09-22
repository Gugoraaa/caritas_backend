from flask import Blueprint, Response, current_app, jsonify, request

from ...errors import HttpException

blueprint = Blueprint("historial", __name__)

TIPOS_VALIDOS = ("todos", "donativos", "llamadas")


@blueprint.get("/historial")
def buscar() -> Response:
    historial = current_app.extensions["historial"]
    return jsonify(
        historial.buscar(_parse_donante_id(), _parse_tipo(), request.args.get("q"))
    )


def _parse_donante_id() -> int | None:
    raw = request.args.get("donante_id")
    if raw is None or raw == "":
        return None
    if not raw.isdigit():
        raise HttpException(400, "donante_id debe ser un entero")
    return int(raw)


def _parse_tipo() -> str:
    tipo = request.args.get("tipo", "todos")
    if tipo not in TIPOS_VALIDOS:
        raise HttpException(400, f"tipo debe ser uno de {TIPOS_VALIDOS}")
    return tipo
