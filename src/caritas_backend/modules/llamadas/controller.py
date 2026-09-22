from flask import Blueprint, Response, current_app, jsonify, request

from ...errors import HttpException

blueprint = Blueprint("calls", __name__)


@blueprint.get("/calls/scheduled")
def get_scheduled_calls() -> Response:
    user_id = _parse_user_id()
    calls_service = current_app.extensions["calls"]
    return jsonify(calls_service.get_scheduled_today_tomorrow(user_id))


def _parse_user_id() -> int:
    raw = request.args.get("user_id")
    if not raw or not raw.isdigit():
        raise HttpException(400, "user_id must be an integer")
    return int(raw)
