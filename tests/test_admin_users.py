import pytest
from flask import Flask

from caritas_backend.errors import HttpException, register_error_handlers
from caritas_backend.modules.admin_usuarios.controller import blueprint
from caritas_backend.modules.admin_usuarios.service import (
    AdminUsersService,
    to_public_user,
)
from caritas_backend.modules.auth.service import AuthService
from caritas_backend.security import sign_token

SECRET = "test-secret"

ROW = {"id": 7, "name": "Lucía Fernández", "role": "admin"}
ROW_COORDINATOR = {"id": 1, "name": "Diego Ocejo", "role": "coordinador"}


def test_maps_row_to_public_user():
    assert to_public_user(ROW) == {"id": 7, "name": "Lucía Fernández", "role": "admin"}


def test_public_user_has_no_password_hash_or_invented_status():
    public = to_public_user({**ROW, "password_hash": "xxx"})
    assert set(public) == {"id", "name", "role"}
    assert "password_hash" not in public
    assert "status" not in public


class FakeAdminUsersRepository:
    def __init__(self, rows=(), error=None):
        self.rows = list(rows)
        self.error = error

    def find_users(self):
        if self.error:
            raise self.error
        return self.rows


def make_service(repository):
    service = AdminUsersService.__new__(AdminUsersService)
    service.users = repository
    return service


def test_repository_errors_are_500():
    service = make_service(FakeAdminUsersRepository(error=RuntimeError("db down")))
    with pytest.raises(HttpException) as error:
        service.list_users()
    assert error.value.status == 500


class FakeUsers:
    ROLES = {6: "Admin", 7: "admin", 1: "coordinador"}

    def find_by_id(self, user_id):
        role = self.ROLES.get(user_id)
        return {"id": user_id, "role": role} if role else None


@pytest.fixture
def repository():
    return FakeAdminUsersRepository([ROW, ROW_COORDINATOR])


@pytest.fixture
def client(repository):
    app = Flask(__name__)
    auth = AuthService(None, SECRET, 3600)
    auth.users = FakeUsers()
    app.extensions["auth"] = auth
    app.extensions["admin_users"] = make_service(repository)
    register_error_handlers(app)
    app.register_blueprint(blueprint)
    return app.test_client()


def bearer(user_id, role="admin"):
    token = sign_token({"userId": user_id, "role": role}, SECRET, 3600)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize("user_id", [6, 7])
def test_endpoint_returns_users_to_admins(client, user_id):
    response = client.get("/admin/users", headers=bearer(user_id))
    assert response.status_code == 200
    assert response.get_json() == [
        {"id": 7, "name": "Lucía Fernández", "role": "admin"},
        {"id": 1, "name": "Diego Ocejo", "role": "coordinador"},
    ]


def test_endpoint_without_token_is_401(client):
    response = client.get("/admin/users")
    assert response.status_code == 401
    assert response.get_json()["statusCode"] == 401


def test_endpoint_with_invalid_token_is_401(client):
    headers = {"Authorization": "Bearer no-es-un-token"}
    response = client.get("/admin/users", headers=headers)
    assert response.status_code == 401


def test_endpoint_with_other_role_is_403(client):
    response = client.get("/admin/users", headers=bearer(1, "coordinador"))
    assert response.status_code == 403
    assert response.get_json() == {
        "message": "Admin role required",
        "error": "Forbidden",
        "statusCode": 403,
    }


def test_endpoint_maps_db_failure_to_500(client):
    failing = FakeAdminUsersRepository(error=RuntimeError("db down"))
    client.application.extensions["admin_users"] = make_service(failing)
    response = client.get("/admin/users", headers=bearer(7))
    assert response.status_code == 500
    assert response.get_json()["statusCode"] == 500
