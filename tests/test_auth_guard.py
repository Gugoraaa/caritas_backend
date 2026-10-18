import time

import pytest
from flask import Flask

from caritas_backend.errors import HttpException
from caritas_backend.modules.auth.guard import (
    ADMIN_REQUIRED,
    INVALID_TOKEN,
    MISSING_TOKEN,
    is_admin,
    optional_user,
    require_admin,
    require_auth,
    user_id_from_token_or_query,
)
from caritas_backend.modules.auth.service import AuthService
from caritas_backend.security import sign_token

SECRET = "test-secret"


@pytest.fixture
def app():
    app = Flask(__name__)
    app.extensions["auth"] = AuthService(None, SECRET, 3600)
    return app


def bearer(payload, secret=SECRET, expires_in=3600):
    return {"Authorization": f"Bearer {sign_token(payload, secret, expires_in)}"}


def assert_401(run, message=INVALID_TOKEN):
    with pytest.raises(HttpException) as error:
        run()
    assert error.value.status == 401
    assert error.value.message == message


def test_without_header_there_is_no_user(app):
    with app.test_request_context("/"):
        assert optional_user() is None


def test_valid_token_exposes_user_id_and_role(app):
    headers = bearer({"userId": 7, "role": "admin"})
    with app.test_request_context("/", headers=headers):
        assert optional_user() == {"userId": 7, "role": "admin"}


@pytest.mark.parametrize(
    "headers",
    [
        {"Authorization": "Bearer basura"},
        {"Authorization": "Basic abc"},
        {"Authorization": "Bearer"},
        bearer({"userId": 7, "role": "admin"}, secret="otro-secreto"),
        bearer({"userId": 7, "role": "admin"}, expires_in=-10),
        bearer({"role": "admin"}),
        bearer({"userId": "7", "role": "admin"}),
    ],
)
def test_invalid_tokens_are_401(app, headers):
    with app.test_request_context("/", headers=headers):
        assert_401(optional_user)


def test_require_auth_rejects_missing_token(app):
    view = require_auth(lambda user: user)
    with app.test_request_context("/"):
        assert_401(view, MISSING_TOKEN)


def test_require_auth_passes_user_to_view(app):
    view = require_auth(lambda user: user)
    with app.test_request_context("/", headers=bearer({"userId": 3, "role": "x"})):
        assert view() == {"userId": 3, "role": "x"}


def test_token_wins_over_query_user_id(app):
    headers = bearer({"userId": 7, "role": "admin"})
    with app.test_request_context("/?user_id=2", headers=headers):
        assert user_id_from_token_or_query() == 7


def test_query_user_id_still_works_without_token(app):
    with app.test_request_context("/?user_id=2"):
        assert user_id_from_token_or_query() == 2


def test_missing_user_id_without_token_is_400(app):
    with app.test_request_context("/"), pytest.raises(HttpException) as error:
        user_id_from_token_or_query()
    assert error.value.status == 400


def test_signed_token_expires_in_the_future():
    service = AuthService(None, SECRET, 3600)
    token = sign_token({"userId": 1, "role": "admin"}, SECRET, 3600)
    assert service.verify(token)["exp"] > time.time()


class FakeUsers:
    def __init__(self, roles=None, error=None):
        self.roles = roles or {}
        self.error = error

    def find_by_id(self, user_id):
        if self.error:
            raise self.error
        role = self.roles.get(user_id)
        return {"id": user_id, "role": role} if role is not None else None


def admin_view(app, roles=None, error=None):
    app.extensions["auth"].users = FakeUsers(roles, error)
    return require_admin(lambda user: user)


def run_status(view):
    with pytest.raises(HttpException) as error:
        view()
    return error.value


@pytest.mark.parametrize("role", ["admin", "Admin", " ADMIN "])
def test_require_admin_accepts_admin_role_in_any_case(app, role):
    view = admin_view(app, {6: role})
    with app.test_request_context("/", headers=bearer({"userId": 6, "role": role})):
        assert view() == {"userId": 6, "role": role}


def test_require_admin_rejects_missing_token(app):
    view = admin_view(app, {6: "admin"})
    with app.test_request_context("/"):
        assert_401(view, MISSING_TOKEN)


def test_require_admin_rejects_invalid_token(app):
    view = admin_view(app, {6: "admin"})
    with app.test_request_context("/", headers={"Authorization": "Bearer basura"}):
        assert_401(view)


def test_require_admin_is_403_for_other_roles(app):
    view = admin_view(app, {1: "coordinador"})
    with app.test_request_context("/", headers=bearer({"userId": 1, "role": "x"})):
        error = run_status(view)
    assert error.body() == {
        "message": ADMIN_REQUIRED,
        "error": "Forbidden",
        "statusCode": 403,
    }


def test_require_admin_reads_role_from_db_not_from_token(app):
    view = admin_view(app, {1: "coordinador"})
    headers = bearer({"userId": 1, "role": "admin"})
    with app.test_request_context("/", headers=headers):
        assert run_status(view).status == 403


def test_require_admin_is_401_when_token_user_no_longer_exists(app):
    view = admin_view(app, {})
    with app.test_request_context("/", headers=bearer({"userId": 9, "role": "admin"})):
        assert_401(view)


def test_require_admin_is_500_when_db_fails(app):
    view = admin_view(app, error=RuntimeError("db down"))
    with app.test_request_context("/", headers=bearer({"userId": 6, "role": "admin"})):
        assert run_status(view).status == 500


@pytest.mark.parametrize(
    ("role", "expected"),
    [("admin", True), ("Admin", True), ("coordinador", False), (None, False)],
)
def test_is_admin(role, expected):
    assert is_admin(role) is expected
