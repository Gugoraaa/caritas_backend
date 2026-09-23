from flask import Blueprint, Response, current_app, jsonify, request

from ...errors import HttpException
from .service import HISTORY_TYPES

blueprint = Blueprint("history", __name__)


@blueprint.get("/history")
def get_history() -> Response:
    history_service = current_app.extensions["history"]
    return jsonify(
        history_service.get_history(
            _parse_user_id(),
            _parse_donor_id(),
            _parse_choice("type", HISTORY_TYPES) or "all",
            _parse_search(),
        )
    )


@blueprint.get("/history/donors")
def get_history_donors() -> Response:
    history_service = current_app.extensions["history"]
    return jsonify(history_service.get_donors(_parse_user_id()))


def _parse_user_id() -> int:
    raw = request.args.get("user_id")
    if not raw or not raw.isdigit():
        raise HttpException(400, "user_id must be an integer")
    return int(raw)


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
