from flask import Blueprint, Response, current_app, jsonify

from ..auth.guard import TELEMARKETING_ROLE, AuthUser, require_role

blueprint = Blueprint("seed", __name__)


@blueprint.post("/seed")
@require_role(TELEMARKETING_ROLE)
def seed_pending_calls(user: AuthUser) -> Response:
    calls_service = current_app.extensions["calls"]
    return jsonify(calls_service.seed_pending_today(user["userId"]))
