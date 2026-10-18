from flask import Blueprint, Response, current_app, jsonify

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


@blueprint.get("/collections/reasons")
def get_not_collected_reasons() -> Response:
    return jsonify(get_reasons())


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
