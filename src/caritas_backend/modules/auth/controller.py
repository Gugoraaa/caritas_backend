from flask import Blueprint, Response, current_app, jsonify

from ...rate_limit import rate_limited
from ...validation import is_email, is_not_empty, is_string, validate_body
from .guard import AuthUser, require_auth

blueprint = Blueprint("auth", __name__)

LOGIN_RULES = {
    "email": [
        (is_email, "must be an email"),
        (is_not_empty, "should not be empty"),
        (is_string, "must be a string"),
    ],
    "password": [
        (is_not_empty, "should not be empty"),
        (is_string, "must be a string"),
    ],
}


@blueprint.post("/login")
@rate_limited("login_limiter")
@validate_body(LOGIN_RULES)
def login(body: dict) -> Response:
    auth = current_app.extensions["auth"]
    return jsonify(auth.login(body["email"], body["password"]))


@blueprint.get("/me")
@require_auth
def me(user: AuthUser) -> Response:
    auth = current_app.extensions["auth"]
    return jsonify(auth.me(user["userId"]))
