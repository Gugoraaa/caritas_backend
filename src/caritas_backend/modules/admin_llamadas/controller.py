from flask import Blueprint, Response, current_app, jsonify, request

from ...errors import HttpException
from ..auth.guard import AuthUser, require_admin

blueprint = Blueprint("admin_calls", __name__)


@blueprint.get("/admin/calls")
@require_admin
def list_calls(user: AuthUser) -> Response:
    admin_calls_service = current_app.extensions["admin_calls"]
    return jsonify(admin_calls_service.list_calls(user_id=_parse_int("user_id")))


def _parse_int(name: str) -> int | None:
    raw = request.args.get(name)
    if not raw:
        return None
    if not raw.isdigit():
        raise HttpException(400, f"{name} must be an integer")
    return int(raw)
