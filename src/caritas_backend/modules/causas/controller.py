from flask import Blueprint, Response, current_app, jsonify

from ...validation import is_not_empty, is_number, is_string, optional, validate_body
from ..auth.guard import AuthUser, require_admin

blueprint = Blueprint("causas", __name__)

CREATE_RULES = {
    "titulo": [
        (is_not_empty, "should not be empty"),
        (is_string, "must be a string"),
    ],
    "monto_objetivo": [(is_number, "must be a number")],
    "descripcion": [(optional(is_string), "must be a string")],
    "beneficiario": [(optional(is_string), "must be a string")],
    "responsable": [(optional(is_string), "must be a string")],
    "lugar": [(optional(is_string), "must be a string")],
    "fecha_fin": [(optional(is_string), "must be a string")],
}

UPDATE_RULES = {
    "titulo": [(optional(is_string), "must be a string")],
    "monto_objetivo": [(optional(is_number), "must be a number")],
    "descripcion": [(optional(is_string), "must be a string")],
    "beneficiario": [(optional(is_string), "must be a string")],
    "responsable": [(optional(is_string), "must be a string")],
    "lugar": [(optional(is_string), "must be a string")],
    "fecha_fin": [(optional(is_string), "must be a string")],
}


@blueprint.get("/causas")
def list_causas() -> Response:
    causa_service = current_app.extensions["causas"]
    return jsonify(causa_service.list_all())


@blueprint.get("/causas/<int:causa_id>")
def get_causa(causa_id: int) -> Response:
    causa_service = current_app.extensions["causas"]
    return jsonify(causa_service.get_detail(causa_id))


@blueprint.post("/causas")
@require_admin
@validate_body(CREATE_RULES)
def create_causa(body: dict, user: AuthUser) -> tuple[Response, int]:
    causa_service = current_app.extensions["causas"]
    return jsonify(causa_service.create(body)), 201


@blueprint.put("/causas/<int:causa_id>")
@require_admin
@validate_body(UPDATE_RULES)
def update_causa(causa_id: int, body: dict, user: AuthUser) -> Response:
    causa_service = current_app.extensions["causas"]
    return jsonify(causa_service.update(causa_id, body))


@blueprint.delete("/causas/<int:causa_id>")
@require_admin
def delete_causa(causa_id: int, user: AuthUser) -> tuple[Response, int]:
    causa_service = current_app.extensions["causas"]
    causa_service.delete(causa_id)
    return jsonify({}), 204
