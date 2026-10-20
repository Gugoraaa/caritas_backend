from flask import Blueprint, Response, current_app, jsonify, request

from ...errors import HttpException
from ..auth.guard import TELEMARKETING_ROLE, AuthUser, require_role
from .service import HISTORY_TYPES

blueprint = Blueprint("history", __name__)


@blueprint.get("/history")
@require_role(TELEMARKETING_ROLE)
def get_history(user: AuthUser) -> Response:
    history_service = current_app.extensions["history"]
    return jsonify(
        history_service.get_history(
            user["userId"],
            _parse_donor_id(),
            _parse_choice("type", HISTORY_TYPES) or "all",
            _parse_search(),
        )
    )


@blueprint.get("/history/donors")
@require_role(TELEMARKETING_ROLE)
def get_history_donors(user: AuthUser) -> Response:
    history_service = current_app.extensions["history"]
    return jsonify(history_service.get_donors(user["userId"]))


def _parse_donor_id() -> int | None:
    raw = request.args.get("donor_id")
    if not raw:
        return None
    if not raw.isdigit():
        raise HttpException(400, "donor_id must be an integer")
    return int(raw)


def _parse_choice(name: str, choices: tuple[str, ...]) -> str | None:
    value = request.args.get(name)
    if not value:
        return None
    if value not in choices:
        raise HttpException(400, f"{name} must be one of {list(choices)}")
    return value


def _parse_search() -> str | None:
    search = (request.args.get("q") or "").strip()
    return search or None
