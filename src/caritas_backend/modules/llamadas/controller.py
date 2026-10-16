from flask import Blueprint, Response, current_app, jsonify, request

from ...errors import HttpException
from ...validation import (
    is_integer,
    is_number,
    is_string,
    one_of,
    optional,
    validate_body,
)
from .service import CALL_RESULTS

blueprint = Blueprint("calls", __name__)

REGISTER_RULES = {
    "llamada_id": [(is_integer, "must be an integer")],
    "user_id": [(is_integer, "must be an integer")],
    "resultado": [(one_of(CALL_RESULTS), f"must be one of {list(CALL_RESULTS)}")],
    "monto_comprometido": [(optional(is_number), "must be a number")],
    "notas": [(optional(is_string), "must be a string")],
    "fecha_seguimiento": [(optional(is_string), "must be a string")],
}


@blueprint.get("/calls/scheduled")
def get_scheduled_calls() -> Response:
    user_id = _parse_user_id()
    calls_service = current_app.extensions["calls"]
    return jsonify(calls_service.get_scheduled_today_tomorrow(user_id))


@blueprint.post("/registro/llamada")
@validate_body(REGISTER_RULES)
def register_call(body: dict) -> Response:
    calls_service = current_app.extensions["calls"]
    return jsonify(calls_service.register_call(body))


def _parse_user_id() -> int:
    raw = request.args.get("user_id")
    if not raw or not raw.isdigit():
        raise HttpException(400, "user_id must be an integer")
    return int(raw)
