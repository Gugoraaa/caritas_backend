from flask import Blueprint, Response, current_app, jsonify, request

from ...errors import HttpException

blueprint = Blueprint("calls", __name__)


@blueprint.get("/calls/scheduled")
def get_scheduled_calls() -> Response:
    """Llamadas agendadas
    ---
    get:
      summary: Obtiene el perfil de los donantes para las llamadas agendadas para hoy y manana
      description: Se usa en la pantalla principal de las telemarketinas en donde ven las llamadas agendadas para el dia de hoy y manana. Tambien sirve para que las telemarketinas vean el semaforo de los donantes y su progreso con las llamadas.
      tags:
        - Calls
      parameters:
        - in: query
          name: user_id
          schema:
            type: integer
          required: true
      responses:
        200:
          description: Llamadas agendadas
          content:
            application/json:
              schema:
                type: array
                items:
                  type: object
                  properties:
                    donor_id:
                      type: integer
                    name:
                      type: string
                    last_name:
                      type: string
                    mother_last_name:
                      type: string
                    call_id:
                      type: integer
                    call_status:
                      type: string
                    scheduled_date:
                      type: string
                      format: date-time
                    days_since_last_payment:
                      type: integer
                      nullable: true
                    latest_payment_amount:
                      type: number
                      nullable: true
                    status_color:
                      type: string
                      enum: [green, yellow, red]
        400:
          description: user_id invalido
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
    user_id = _parse_user_id()
    calls_service = current_app.extensions["calls"]
    return jsonify(calls_service.get_scheduled_today_tomorrow(user_id))


def _parse_user_id() -> int:
    raw = request.args.get("user_id")
    if not raw or not raw.isdigit():
        raise HttpException(400, "user_id must be an integer")
    return int(raw)
