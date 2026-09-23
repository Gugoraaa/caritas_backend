from flask import Blueprint, Response, current_app, jsonify

blueprint = Blueprint("donantes", __name__)


@blueprint.get("/donantes")
def listar() -> Response:
    """Listar donantes
    ---
    get:
      summary: Listar donantes
      description: Devuelve todos los donantes registrados, ordenados segun la consulta.
      tags:
        - Donantes
      responses:
        200:
          description: Lista de donantes
          content:
            application/json:
              schema:
                type: array
                items:
                  type: object
                  properties:
                    id:
                      type: integer
                    nombre:
                      type: string
        500:
          description: Error interno del servidor
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/Error"
    """
    donantes = current_app.extensions["donantes"]
    return jsonify(donantes.list_donantes())
