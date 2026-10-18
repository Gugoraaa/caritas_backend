from flask import Blueprint, Response, current_app, jsonify

from ...validation import (
    is_in,
    is_not_empty,
    is_number,
    is_string,
    max_length,
    min_value,
    optional,
    validate_body,
)
from ..auth.guard import AuthUser, require_auth, user_id_from_token_or_query
from .service import CALL_RESULT_STATES

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
