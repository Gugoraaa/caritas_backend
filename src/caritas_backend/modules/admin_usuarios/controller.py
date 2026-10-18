from flask import Blueprint, Response, current_app, jsonify

from ..auth.guard import AuthUser, require_admin

blueprint = Blueprint("admin_users", __name__)


@blueprint.get("/admin/users")
@require_admin
def list_users(user: AuthUser) -> Response:
    admin_users_service = current_app.extensions["admin_users"]
    return jsonify(admin_users_service.list_users())
