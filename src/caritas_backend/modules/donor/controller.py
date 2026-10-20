from flask import Blueprint, Response, current_app, jsonify

from ..auth.guard import TELEMARKETING_ROLE, AuthUser, require_role

blueprint = Blueprint("donors", __name__)


@blueprint.get("/donors/<int:donor_id>")
@require_role(TELEMARKETING_ROLE)
def get_donor_detail(donor_id: int, user: AuthUser) -> Response:
    donor_service = current_app.extensions["donors"]
    return jsonify(donor_service.get_detail(donor_id))

