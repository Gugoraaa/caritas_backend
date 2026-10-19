from datetime import date

from flask import Blueprint, Response, current_app, jsonify, request

from ...errors import HttpException
from ...validation import is_string, one_of, validate_body
from ..auth.guard import AuthUser, require_auth
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


@blueprint.get("/collections")
@require_auth
def list_collections(user: AuthUser) -> Response:
    collections_service = current_app.extensions["collections"]
    return jsonify(
        collections_service.list_collections(
            request.args.get("status"),
            _parse_int("collector_id"),
            _parse_date("from"),
            _parse_date("to"),
        )
    )


@blueprint.get("/collections/reasons")
def get_not_collected_reasons() -> Response:
    return jsonify(get_reasons())


@blueprint.get("/collections/history")
@require_auth
def get_collection_history(user: AuthUser) -> Response:
    collections_service = current_app.extensions["collections"]
    return jsonify(
        collections_service.get_history(
            user["userId"], _parse_date("from"), _parse_date("to")
        )
    )


@blueprint.get("/collections/<int:collection_id>")
@require_auth
def get_collection(collection_id: int, user: AuthUser) -> Response:
    collections_service = current_app.extensions["collections"]
    return jsonify(collections_service.get_collection(collection_id))


@blueprint.post("/collections/<int:collection_id>/confirm")
@require_auth
def confirm_collection(collection_id: int, user: AuthUser) -> Response:
    collections_service = current_app.extensions["collections"]
    return jsonify(collections_service.confirm(collection_id, user["userId"]))


@blueprint.post("/collections/<int:collection_id>/not-collected")
@require_auth
@validate_body(NOT_COLLECTED_RULES)
def not_collected(collection_id: int, user: AuthUser, body: dict) -> Response:
    collections_service = current_app.extensions["collections"]
    return jsonify(
        collections_service.not_collected(collection_id, body["reason"], user["userId"])
    )


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
