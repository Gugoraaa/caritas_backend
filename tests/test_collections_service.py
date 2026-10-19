from datetime import date, datetime
from decimal import Decimal

import pytest
from flask import Flask

from caritas_backend.errors import HttpException, register_error_handlers
from caritas_backend.modules.auth.service import AuthService
from caritas_backend.modules.recolecciones.controller import blueprint
from caritas_backend.modules.recolecciones.service import (
    CollectionsService,
    format_address,
    get_reasons,
)
from caritas_backend.security import sign_token

SECRET = "test-secret"

ROW = {
    "id": 5,
    "promesa_id": 20,
    "recolector_id": None,
    "fecha_programada": datetime(2026, 10, 18, 10, 45),
    "ventana_inicio": datetime(2026, 10, 18, 10, 30),
    "ventana_fin": datetime(2026, 10, 18, 11, 30),
    "monto": Decimal("300.00"),
    "notas_domicilio": "Departamento 3, segundo piso.",
    "estado": "pendiente",
    "motivo": None,
    "fecha_resultado": None,
    "abono_id": None,
    "donor_id": 3,
    "nombre": "Guadalupe",
    "apellido_paterno": "Sánchez",
    "apellido_materno": "Cavazos",
    "telefono": "8183716620",
    "calle": "Simón Bolívar",
    "numero_exterior": "1108",
    "numero_interior": None,
    "colonia": "Mitras Centro",
    "municipio": "Monterrey",
}

HISTORY_ROW = {
    "id": 5,
    "estado": "confirmada",
    "updated_at": datetime(2026, 10, 18, 10, 55),
    "monto_recolectado": Decimal("300.00"),
    "nombre": "Guadalupe",
    "apellido_paterno": "Sánchez",
    "apellido_materno": "Cavazos",
}


class FakeCollectionsRepository:
    def __init__(self, row=ROW, error=None, abono_id=99, updated=True):
        self.row = row
        self.error = error
        self.abono_id = abono_id
        self.updated = updated
        self.confirmed = None
        self.not_collected = None

    def find_history(self, user_id, since, until):
        if self.error:
            raise self.error
        self.history_args = (user_id, since, until)
        return [HISTORY_ROW]

    def find(self, collection_id):
        if self.error:
            raise self.error
        return self.row

    def confirm(self, collection_id, promise_id, amount, collected_at, user_id):
        self.confirmed = (collection_id, promise_id, amount, user_id)
        return self.abono_id

    def mark_not_collected(self, collection_id, reason, resolved_at, user_id):
        self.not_collected = (collection_id, reason, user_id)
        return self.updated


def make_service(repository):
    service = CollectionsService.__new__(CollectionsService)
    service.collections = repository
    return service


def test_collection_detail():
    detail = make_service(FakeCollectionsRepository()).get_collection(5)

    assert detail == {
        "id": 5,
        "promise_id": 20,
        "donor_id": 3,
        "name": "Guadalupe",
        "last_name": "Sánchez",
        "mother_last_name": "Cavazos",
        "phone": "8183716620",
        "address": "Simón Bolívar 1108, Col. Mitras Centro, Monterrey",
        "interior_number": None,
        "address_notes": "Departamento 3, segundo piso.",
        "scheduled_at": "2026-10-18T10:45:00",
        "window_start": "2026-10-18T10:30:00",
        "window_end": "2026-10-18T11:30:00",
        "amount": Decimal("300.00"),
        "status": "pendiente",
        "reason": None,
        "reason_label": None,
        "resolved_at": None,
        "abono_id": None,
    }


def test_history_items():
    repository = FakeCollectionsRepository()

    history = make_service(repository).get_history(7, None, None)

    assert repository.history_args == (7, None, None)
    assert history == [
        {
            "id": 5,
            "name": "Guadalupe",
            "last_name": "Sánchez",
            "mother_last_name": "Cavazos",
            "date": "2026-10-18T10:55:00",
            "status": "confirmada",
            "amount": Decimal("300.00"),
        }
    ]


def test_history_dates_are_inclusive_days():
    repository = FakeCollectionsRepository()

    make_service(repository).get_history(7, date(2026, 10, 1), date(2026, 10, 18))

    assert repository.history_args == (
        7,
        datetime(2026, 10, 1),
        datetime(2026, 10, 19),
    )


def test_history_rejects_inverted_range():
    with pytest.raises(HttpException) as error:
        make_service(FakeCollectionsRepository()).get_history(
            7, date(2026, 10, 18), date(2026, 10, 1)
        )
    assert error.value.status == 400


def test_history_database_error_becomes_500():
    service = make_service(FakeCollectionsRepository(error=RuntimeError("db down")))
    with pytest.raises(HttpException) as error:
        service.get_history(7, None, None)
    assert error.value.status == 500


@pytest.fixture
def client():
    repository = FakeCollectionsRepository()
    app = Flask(__name__)
    app.extensions["auth"] = AuthService(None, SECRET, 3600)
    app.extensions["collections"] = make_service(repository)
    register_error_handlers(app)
    app.register_blueprint(blueprint)
    client = app.test_client()
    client.repository = repository
    return client


def bearer(user_id):
    token = sign_token({"userId": user_id, "role": "recolector"}, SECRET, 3600)
    return {"Authorization": f"Bearer {token}"}


def test_history_endpoint_uses_token_user_and_dates(client):
    response = client.get(
        "/collections/history?from=2026-10-01&to=2026-10-18", headers=bearer(7)
    )

    assert response.status_code == 200
    assert response.get_json()[0]["amount"] == "300.00"
    assert client.repository.history_args == (
        7,
        datetime(2026, 10, 1),
        datetime(2026, 10, 19),
    )


def test_history_endpoint_rejects_bad_date(client):
    response = client.get("/collections/history?from=18/10/2026", headers=bearer(7))
    assert response.status_code == 400


def test_history_endpoint_without_token_is_401(client):
    assert client.get("/collections/history").status_code == 401


def test_confirm_creates_abono_for_the_collection_amount():
    repository = FakeCollectionsRepository()

    detail = make_service(repository).confirm(5, user_id=7)

    assert repository.confirmed == (5, 20, Decimal("300.00"), 7)
    assert detail["status"] == "confirmada"
    assert detail["abono_id"] == 99
    assert detail["resolved_at"] is not None


def test_not_collected_saves_reason():
    repository = FakeCollectionsRepository()

    detail = make_service(repository).not_collected(5, "reprogramar", user_id=7)

    assert repository.not_collected == (5, "reprogramar", 7)
    assert detail["status"] == "no_recolectada"
    assert detail["reason"] == "reprogramar"
    assert detail["reason_label"] == "El donante pidió reprogramar"


@pytest.mark.parametrize("estado", ["confirmada", "no_recolectada"])
def test_resolved_collection_cannot_change(estado):
    repository = FakeCollectionsRepository({**ROW, "estado": estado})
    service = make_service(repository)

    for action in (
        lambda: service.confirm(5, user_id=7),
        lambda: service.not_collected(5, "reprogramar", user_id=7),
    ):
        with pytest.raises(HttpException) as error:
            action()
        assert error.value.status == 409
    assert repository.confirmed is None
    assert repository.not_collected is None


def test_concurrent_resolution_becomes_409():
    service = make_service(FakeCollectionsRepository(abono_id=None, updated=False))

    with pytest.raises(HttpException) as error:
        service.confirm(5, user_id=7)
    assert error.value.status == 409

    with pytest.raises(HttpException) as error:
        service.not_collected(5, "reprogramar", user_id=7)
    assert error.value.status == 409


def test_not_found():
    with pytest.raises(HttpException) as error:
        make_service(FakeCollectionsRepository(row=None)).get_collection(1)
    assert error.value.status == 404


def test_database_error_becomes_500():
    service = make_service(FakeCollectionsRepository(error=RuntimeError("db down")))
    with pytest.raises(HttpException) as error:
        service.get_collection(5)
    assert error.value.status == 500


def test_address_without_optional_parts():
    row = {**ROW, "numero_exterior": None, "colonia": None}
    assert format_address(row) == "Simón Bolívar, Monterrey"
    assert format_address({**row, "calle": None, "municipio": None}) is None


def test_reasons_catalog():
    assert [r["code"] for r in get_reasons()] == [
        "nadie_en_domicilio",
        "reprogramar",
        "domicilio_incorrecto",
        "ya_no_desea_donar",
    ]
