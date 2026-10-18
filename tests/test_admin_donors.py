from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from flask import Flask

from caritas_backend.errors import HttpException, register_error_handlers
from caritas_backend.modules.admin.controller import blueprint
from caritas_backend.modules.admin.service import AdminService, to_admin_donor
from caritas_backend.modules.auth.service import AuthService
from caritas_backend.security import sign_token

SECRET = "test-secret"
TODAY = date(2026, 10, 17)

ROW = {
    "id": 4,
    "nombre": "María",
    "apellido_paterno": "Gómez",
    "apellido_materno": None,
    "colonia": "Obispado",
    "causa_id": 3,
    "causa_titulo": "Rehabilitación del comedor comunitario",
    "ultima_donacion_fecha": datetime(2026, 9, 27),
    "ultima_donacion_monto": Decimal("5500.00"),
    "metodo_pago": "spei",
}

NO_PROMISES = {
    **ROW,
    "id": 9,
    "nombre": "Ana",
    "causa_id": None,
    "causa_titulo": None,
    "ultima_donacion_fecha": None,
    "ultima_donacion_monto": None,
    "metodo_pago": None,
}


def test_maps_row_to_admin_donor():
    assert to_admin_donor(ROW, TODAY) == {
        "id": 4,
        "full_name": "María Gómez",
        "initials": "MG",
        "neighborhood": "Obispado",
        "causa": {
            "id": 3,
            "titulo": "Rehabilitación del comedor comunitario",
            "clave": "RC",
            "nombre_corto": "Rehabilitación",
        },
        "last_donation_at": "2026-09-27T00:00:00",
        "last_donation_amount": Decimal("5500.00"),
        "payment_method": "spei",
        "risk": {"level": "green", "days_without_donating": 20},
    }


def test_donor_without_promises_has_null_causa_and_red_risk():
    donor = to_admin_donor(NO_PROMISES, TODAY)
    assert donor["causa"] is None
    assert donor["last_donation_at"] is None
    assert donor["payment_method"] is None
    assert donor["risk"] == {"level": "red", "days_without_donating": None}


@pytest.mark.parametrize(
    ("days", "level"), [(29, "green"), (30, "yellow"), (60, "red")]
)
def test_risk_uses_donor_rule(days, level):
    row = {**ROW, "ultima_donacion_fecha": datetime(2026, 10, 17) - timedelta(days)}
    assert to_admin_donor(row, TODAY)["risk"]["level"] == level


class FakeAdminRepository:
    def __init__(self, rows=(), error=None):
        self.rows = list(rows)
        self.error = error
        self.received = []

    def find_donors(self, search, causa_id, metodo):
        self.received.append((search, causa_id, metodo))
        if self.error:
            raise self.error
        return self.rows


def make_service(repository):
    service = AdminService.__new__(AdminService)
    service.admin = repository
    return service


def test_risk_filter_is_applied_after_computing_risk():
    service = make_service(FakeAdminRepository([ROW, NO_PROMISES]))
    assert [donor["id"] for donor in service.list_donors(risk="red")] == [9]


def test_repository_errors_are_500():
    service = make_service(FakeAdminRepository(error=RuntimeError("db down")))
    with pytest.raises(HttpException) as error:
        service.list_donors()
    assert error.value.status == 500


class FakeUsers:
    ROLES = {6: "Admin", 7: "admin", 1: "coordinador"}

    def find_by_id(self, user_id):
        role = self.ROLES.get(user_id)
        return {"id": user_id, "role": role} if role else None


@pytest.fixture
def repository():
    return FakeAdminRepository([ROW])


@pytest.fixture
def client(repository):
    app = Flask(__name__)
    auth = AuthService(None, SECRET, 3600)
    auth.users = FakeUsers()
    app.extensions["auth"] = auth
    app.extensions["admin"] = make_service(repository)
    register_error_handlers(app)
    app.register_blueprint(blueprint)
    return app.test_client()


def bearer(user_id, role="admin"):
    token = sign_token({"userId": user_id, "role": role}, SECRET, 3600)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize("user_id", [6, 7])
def test_endpoint_returns_donors_to_admins(client, user_id):
    response = client.get("/admin/donors", headers=bearer(user_id))
    assert response.status_code == 200
    body = response.get_json()
    assert body[0]["causa"]["clave"] == "RC"
    assert body[0]["last_donation_amount"] == "5500.00"


def test_endpoint_without_token_is_401(client):
    response = client.get("/admin/donors")
    assert response.status_code == 401
    assert response.get_json()["statusCode"] == 401


def test_endpoint_with_other_role_is_403(client):
    response = client.get("/admin/donors", headers=bearer(1, "coordinador"))
    assert response.status_code == 403
    assert response.get_json() == {
        "message": "Admin role required",
        "error": "Forbidden",
        "statusCode": 403,
    }


def test_endpoint_passes_filters(client, repository):
    response = client.get(
        "/admin/donors?q=%20maria%20&causa_id=3&metodo=spei&risk=green",
        headers=bearer(7),
    )
    assert response.status_code == 200
    assert repository.received == [("maria", 3, "spei")]


@pytest.mark.parametrize(
    ("query", "message"),
    [
        ("risk=rojo", "risk must be one of ['green', 'yellow', 'red']"),
        ("metodo=tarjeta", "metodo must be one of ['efectivo', 'spei']"),
        ("causa_id=abc", "causa_id must be an integer"),
    ],
)
def test_endpoint_rejects_invalid_filters(client, repository, query, message):
    response = client.get(f"/admin/donors?{query}", headers=bearer(7))
    assert response.status_code == 400
    assert response.get_json()["message"] == message
    assert repository.received == []
