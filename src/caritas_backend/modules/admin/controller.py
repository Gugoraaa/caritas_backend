from flask import Blueprint, Response, current_app, jsonify, request

from ...errors import HttpException
from ..auth.guard import AuthUser, require_admin
from .service import PAYMENT_METHODS, RISK_LEVELS

blueprint = Blueprint("admin", __name__)


@blueprint.get("/admin/donors")
@require_admin
def list_donors(user: AuthUser) -> Response:
    admin_service = current_app.extensions["admin"]
    return jsonify(
        admin_service.list_donors(
            search=(request.args.get("q") or "").strip() or None,
            risk=_parse_choice("risk", RISK_LEVELS),
            causa_id=_parse_int("causa_id"),
            metodo=_parse_choice("metodo", PAYMENT_METHODS),
        )
    )


def _parse_int(name: str) -> int | None:
    raw = request.args.get(name)
    if not raw:
        return None
    if not raw.isdigit():
        raise HttpException(400, f"{name} must be an integer")
    return int(raw)


def _parse_choice(name: str, choices: tuple[str, ...]) -> str | None:
    value = request.args.get(name)
    if not value:
        return None
    if value not in choices:
        raise HttpException(400, f"{name} must be one of {list(choices)}")
    return value
