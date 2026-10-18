from flask import Blueprint, Response, current_app, jsonify

from ...validation import (
    is_in,
    is_integer,
    is_not_empty,
    is_number,
    is_string,
    max_length,
    min_value,
    one_of,
    optional,
    validate_body,
)
from ..auth.guard import AuthUser, require_auth, user_id_from_token_or_query
from .service import CALL_RESULT_STATES, CALL_RESULTS

blueprint = Blueprint("calls", __name__)

UPDATE_RULES = {
    "resultado_llamado": [
        (is_not_empty, "should not be empty"),
        (is_string, "must be a string"),
    ],
    "proposito": [
        (optional(is_string), "must be a string"),
        (optional(max_length(30)), "must be shorter than or equal to 30 characters"),
    ],
    "monto_comprometido": [
        (optional(is_number), "must be a number"),
        (optional(min_value(0)), "must not be less than 0"),
    ],
    "estado": [
        (
            optional(is_in(CALL_RESULT_STATES)),
            f"must be one of {list(CALL_RESULT_STATES)}",
        ),
    ],
}

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
    user_id = user_id_from_token_or_query()
    calls_service = current_app.extensions["calls"]
    return jsonify(calls_service.get_scheduled_today_tomorrow(user_id))


@blueprint.patch("/calls/<int:call_id>")
@require_auth
@validate_body(UPDATE_RULES)
def update_call(call_id: int, body: dict, user: AuthUser) -> Response:
    calls_service = current_app.extensions["calls"]
    return jsonify(calls_service.record_result(call_id, body, user))


@blueprint.post("/registro/llamada")
@validate_body(REGISTER_RULES)
def register_call(body: dict) -> Response:
    calls_service = current_app.extensions["calls"]
    return jsonify(calls_service.register_call(body))
