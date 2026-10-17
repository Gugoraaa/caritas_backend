from decimal import Decimal

from flask import Blueprint, Response, current_app, jsonify

from ...validation import is_number, is_string, one_of, optional, validate_body
from .service import NOT_COLLECTED_REASONS, get_reasons

blueprint = Blueprint("collections", __name__)

CONFIRM_RULES = {
    "monto": [(optional(is_number), "must be a number")],
}

NOT_COLLECTED_RULES = {
    "reason": [
        (is_string, "must be a string"),
        (
            one_of(tuple(NOT_COLLECTED_REASONS)),
            f"must be one of {list(NOT_COLLECTED_REASONS)}",
        ),
    ],
}


@blueprint.get("/collections/reasons")
def get_not_collected_reasons() -> Response:
    return jsonify(get_reasons())


@blueprint.get("/collections/<int:promise_id>")
def get_collection(promise_id: int) -> Response:
    collections_service = current_app.extensions["collections"]
    return jsonify(collections_service.get_collection(promise_id))


@blueprint.post("/collections/<int:promise_id>/confirm")
@validate_body(CONFIRM_RULES)
def confirm_collection(promise_id: int, body: dict) -> tuple[Response, int]:
    collections_service = current_app.extensions["collections"]
    amount = body.get("monto")
    # str() evita arrastrar el error binario del float.
    amount = Decimal(str(amount)) if amount is not None else None
    return jsonify(collections_service.confirm(promise_id, amount)), 201


@blueprint.post("/collections/<int:promise_id>/not-collected")
@validate_body(NOT_COLLECTED_RULES)
def not_collected(promise_id: int, body: dict) -> Response:
    collections_service = current_app.extensions["collections"]
    return jsonify(collections_service.not_collected(promise_id, body["reason"]))
