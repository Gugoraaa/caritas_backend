from datetime import datetime

import pytest
from flask import Flask

from caritas_backend.errors import HttpException, register_error_handlers
from caritas_backend.modules.admin_llamadas.controller import blueprint
from caritas_backend.modules.admin_llamadas.service import (
    AdminCallsService,
    to_public_call,
)
from caritas_backend.modules.auth.service import AuthService
from caritas_backend.security import sign_token

SECRET = "test-secret"

ROW = {
    "call_id": 12,
    "donor_id": 4,
    "donor_full_name": "María Gómez",
    "user_id": 7,
    "user_name": "Lucía Fernández",
    "result": "promesa de donativo",
    "call_status": "completada",
    "scheduled_date": datetime(2026, 10, 17, 10, 30),
}

# Llamada sin responsable asignado (responsable_id NULL) ni fecha agendada.
ROW_UNASSIGNED = {
    **ROW,
    "call_id": 13,
    "user_id": None,
    "user_name": None,
    "call_status": "agendada",
    "result": "pendiente",
    "scheduled_date": None,
}


def test_maps_row_to_public_call():
    assert to_public_call(ROW) == {
        "call_id": 12,
        "donor_id": 4,
        "donor_full_name": "María Gómez",
        "user_id": 7,
        "user_name": "Lucía Fernández",
        "result": "promesa de donativo",
        "call_status": "completada",
        "scheduled_date": "2026-10-17T10:30:00",
    }


def test_unassigned_call_has_null_user_and_scheduled_date():
    call = to_public_call(ROW_UNASSIGNED)
    assert call["user_id"] is None
    assert call["user_name"] is None
    assert call["scheduled_date"] is None


def test_public_call_has_no_payment_or_duration_fields():
    public = to_public_call(ROW)
    assert set(public) == {
        "call_id",
        "donor_id",
        "donor_full_name",
        "user_id",
        "user_name",
        "result",
        "call_status",
        "scheduled_date",
    }


class FakeAdminCallsRepository:
    def __init__(self, rows=(), error=None):
        self.rows = list(rows)
        self.error = error
        self.received = []

    def find_calls(self, user_id):
        self.received.append(user_id)
        if self.error:
            raise self.error
        return self.rows


def make_service(repository):
    service = AdminCallsService.__new__(AdminCallsService)
    service.calls = repository
    return service


@pytest.mark.parametrize("user_id", [None, 5])
def test_service_passes_user_filter_to_repository(user_id):
    repository = FakeAdminCallsRepository([ROW])
    assert make_service(repository).list_calls(user_id=user_id) != []
    assert repository.received == [user_id]


def test_repository_errors_are_500():
    service = make_service(FakeAdminCallsRepository(error=RuntimeError("db down")))
    with pytest.raises(HttpException) as error:
        service.list_calls()
    assert error.value.status == 500


class FakeUsers:
    ROLES = {6: "Admin", 7: "admin", 1: "coordinador"}

    def find_by_id(self, user_id):
        role = self.ROLES.get(user_id)
        return {"id": user_id, "role": role} if role else None


@pytest.fixture
def repository():
    return FakeAdminCallsRepository([ROW, ROW_UNASSIGNED])


@pytest.fixture
def client(repository):
    app = Flask(__name__)
    auth = AuthService(None, SECRET, 3600)
    auth.users = FakeUsers()
    app.extensions["auth"] = auth
    app.extensions["admin_calls"] = make_service(repository)
    register_error_handlers(app)
    app.register_blueprint(blueprint)
    return app.test_client()


def bearer(user_id, role="admin"):
    token = sign_token({"userId": user_id, "role": role}, SECRET, 3600)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize("user_id", [6, 7])
def test_endpoint_returns_calls_to_admins(client, user_id):
    response = client.get("/admin/calls", headers=bearer(user_id))
    assert response.status_code == 200
    body = response.get_json()
    assert len(body) == 2
    assert body[0] == {
        "call_id": 12,
        "donor_id": 4,
        "donor_full_name": "María Gómez",
        "user_id": 7,
        "user_name": "Lucía Fernández",
        "result": "promesa de donativo",
        "call_status": "completada",
        "scheduled_date": "2026-10-17T10:30:00",
    }


def test_endpoint_without_token_is_401(client):
    response = client.get("/admin/calls")
    assert response.status_code == 401
    assert response.get_json()["statusCode"] == 401


def test_endpoint_with_invalid_token_is_401(client):
    headers = {"Authorization": "Bearer no-es-un-token"}
    response = client.get("/admin/calls", headers=headers)
    assert response.status_code == 401


def test_endpoint_with_other_role_is_403(client):
    response = client.get("/admin/calls", headers=bearer(1, "coordinador"))
    assert response.status_code == 403
    assert response.get_json() == {
        "message": "Admin role required",
        "error": "Forbidden",
        "statusCode": 403,
    }


def test_endpoint_passes_user_id_filter(client, repository):
    response = client.get("/admin/calls?user_id=5", headers=bearer(7))
    assert response.status_code == 200
    assert repository.received == [5]


def test_endpoint_rejects_invalid_user_id(client, repository):
    response = client.get("/admin/calls?user_id=abc", headers=bearer(7))
    assert response.status_code == 400
    assert response.get_json()["message"] == "user_id must be an integer"
    assert repository.received == []


def test_endpoint_maps_db_failure_to_500(client):
    failing = FakeAdminCallsRepository(error=RuntimeError("db down"))
    client.application.extensions["admin_calls"] = make_service(failing)
    response = client.get("/admin/calls", headers=bearer(7))
    assert response.status_code == 500
    assert response.get_json()["statusCode"] == 500
