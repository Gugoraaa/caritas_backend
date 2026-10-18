from flask import Blueprint, Response, current_app, jsonify

from ..auth.guard import AuthUser, require_admin
from .service import AdminResumenService

blueprint = Blueprint("admin_resumen", __name__)


@blueprint.get("/admin/summary")
@require_admin
def summary(user: AuthUser) -> Response:
    service: AdminResumenService = current_app.extensions["admin_resumen"]
    return jsonify(service.get_summary())
