from datetime import date

from flask import Blueprint, Response, current_app, jsonify, request

from ...errors import HttpException
from ...validation import (
    is_integer,
    is_string,
    max_length,
    min_value,
    one_of,
    optional,
    validate_body,
)
from ..auth.guard import COURIER_ROLE, AuthUser, is_admin, require_admin, require_role
from .service import NOT_COLLECTED_REASONS, get_reasons

blueprint = Blueprint("collections", __name__)

NOT_COLLECTED_RULES = {
    "reason": [
        (is_string, "must be a string"),
        (
            one_of(tuple(NOT_COLLECTED_REASONS)),
            f"must be one of {list(NOT_COLLECTED_REASONS)}",
        ),
    ],
}

UPDATE_RULES = {
    "collector_id": [(optional(is_integer), "must be an integer")],
    "scheduled_at": [(optional(is_string), "must be an ISO date-time string")],
    "window_start": [(optional(is_string), "must be an ISO date-time string")],
    "window_end": [(optional(is_string), "must be an ISO date-time string")],
    "amount": [(optional(min_value(0.01)), "must be a number greater than 0")],
    "address_notes": [(optional(max_length(500)), "must be a string of at most 500 characters")],
}

CREATE_RULES = {
    "promise_id": [(is_integer, "must be an integer")],
    "scheduled_at": [(is_string, "must be an ISO date-time string")],
    "amount": [(min_value(0.01), "must be a number greater than 0")],
    **{k: v for k, v in UPDATE_RULES.items() if k not in ("scheduled_at", "amount")},
}


@blueprint.post("/collections")
@require_admin
@validate_body(CREATE_RULES)
def create_collection(user: AuthUser, body: dict) -> tuple[Response, int]:
    collections_service = current_app.extensions["collections"]
    return jsonify(collections_service.create(body)), 201


@blueprint.get("/collections")
@require_role(COURIER_ROLE)
def list_collections(user: AuthUser) -> Response:
    collections_service = current_app.extensions["collections"]
    return jsonify(
        collections_service.list_collections(
            request.args.get("status"),
            _parse_int("collector_id") if is_admin(user["role"]) else user["userId"],
            _parse_date("from"),
            _parse_date("to"),
        )
    )


@blueprint.get("/collections/reasons")
def get_not_collected_reasons() -> Response:
    return jsonify(get_reasons())


@blueprint.get("/collections/history")
@require_role(COURIER_ROLE)
def get_collection_history(user: AuthUser) -> Response:
    collections_service = current_app.extensions["collections"]
    return jsonify(
        collections_service.get_history(
            user["userId"], _parse_date("from"), _parse_date("to")
        )
    )


@blueprint.get("/collections/<int:collection_id>")
@require_role(COURIER_ROLE)
def get_collection(collection_id: int, user: AuthUser) -> Response:
    collections_service = current_app.extensions["collections"]
    return jsonify(collections_service.get_collection(collection_id, _owner(user)))


@blueprint.patch("/collections/<int:collection_id>")
@require_admin
@validate_body(UPDATE_RULES)
def update_collection(collection_id: int, user: AuthUser, body: dict) -> Response:
    collections_service = current_app.extensions["collections"]
    return jsonify(collections_service.update(collection_id, body))


@blueprint.delete("/collections/<int:collection_id>")
@require_admin
def delete_collection(collection_id: int, user: AuthUser) -> tuple[str, int]:
    collections_service = current_app.extensions["collections"]
    collections_service.delete(collection_id)
    return "", 204


@blueprint.post("/collections/<int:collection_id>/confirm")
@require_role(COURIER_ROLE)
def confirm_collection(collection_id: int, user: AuthUser) -> Response:
    collections_service = current_app.extensions["collections"]
    return jsonify(
        collections_service.confirm(collection_id, user["userId"], _owner(user))
    )


@blueprint.post("/collections/<int:collection_id>/not-collected")
@require_role(COURIER_ROLE)
@validate_body(NOT_COLLECTED_RULES)
def not_collected(collection_id: int, user: AuthUser, body: dict) -> Response:
    collections_service = current_app.extensions["collections"]
    return jsonify(
        collections_service.not_collected(
            collection_id, body["reason"], user["userId"], _owner(user)
        )
    )


def _owner(user: AuthUser) -> int | None:
    """El repartidor solo puede tocar sus recolecciones; admin, todas."""
    return None if is_admin(user["role"]) else user["userId"]


def _parse_date(name: str) -> date | None:
    raw = request.args.get(name)
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError as error:
        raise HttpException(400, f"{name} must be a date (YYYY-MM-DD)") from error


def _parse_int(name: str) -> int | None:
    raw = request.args.get(name)
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError as error:
        raise HttpException(400, f"{name} must be an integer") from error
