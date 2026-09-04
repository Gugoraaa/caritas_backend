from flask import Blueprint, Response, current_app, jsonify

from ...validation import is_email, is_not_empty, is_string, validate_body

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
@validate_body(LOGIN_RULES)
def login(body: dict) -> Response:
    auth = current_app.extensions["auth"]
    return jsonify(auth.login(body["email"], body["password"]))
