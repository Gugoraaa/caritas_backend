from flask import Blueprint, Response, current_app, jsonify, request

from ...errors import HttpException

blueprint = Blueprint("historial", __name__)

TIPOS_VALIDOS = ("todos", "donativos", "llamadas")


@blueprint.get("/historial")
def buscar() -> Response:
    """Buscar historial
    ---
    get:
      summary: Buscar historial de donativos y llamadas
      tags:
        - Historial
      parameters:
        - in: query
          name: donante_id
          schema:
            type: integer
          required: false
          description: Filtra por un donante especifico
        - in: query
          name: tipo
          schema:
            type: string
            enum: [todos, donativos, llamadas]
            default: todos
          required: false
        - in: query
          name: q
          schema:
            type: string
          required: false
          description: Texto de busqueda libre
      responses:
        200:
          description: Entradas del historial ordenadas por fecha descendente
          content:
            application/json:
              schema:
                type: array
                items:
                  type: object
        400:
          description: Parametros invalidos
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/Error"
        500:
          description: Error interno del servidor
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/Error"
    """
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
