from datetime import datetime
from decimal import Decimal

import pytest

from caritas_backend.errors import HttpException
from caritas_backend.modules.recolecciones.service import (
    CollectionsService,
    format_address,
    get_installment,
    get_reasons,
)

ROW = {
    "promesa_id": 20,
    "state": "activo",
    "monto_objetivo": Decimal("3600.00"),
    "numero_frequencia": 12,
    "donor_id": 3,
    "nombre": "Guadalupe",
    "apellido_paterno": "Sánchez",
    "apellido_materno": "Cavazos",
    "telefono": "8183716620",
    "calle": "Simón Bolívar",
    "numero_exterior": "1108",
    "numero_interior": "Depto 3",
    "colonia": "Mitras Centro",
    "municipio": "Monterrey",
    "total_pagado": Decimal("600.00"),
    "abono_hoy_id": None,
    "abono_hoy_monto": None,
    "abono_hoy_fecha": None,
}


class FakeCollectionsRepository:
    def __init__(self, row=ROW, error=None):
        self.row = row
        self.error = error
        self.inserted = None

    def find(self, promise_id, today):
        if self.error:
            raise self.error
        return self.row

    def insert_abono(self, promise_id, amount, collected_at):
        self.inserted = (promise_id, amount, collected_at)
        return 99


def make_service(repository):
    service = CollectionsService.__new__(CollectionsService)
    service.collections = repository
    return service


def test_pending_collection_detail():
    detail = make_service(FakeCollectionsRepository()).get_collection(20)

    assert detail == {
        "promise_id": 20,
        "donor_id": 3,
        "name": "Guadalupe",
        "last_name": "Sánchez",
        "mother_last_name": "Cavazos",
        "phone": "8183716620",
        "address": "Simón Bolívar 1108, Col. Mitras Centro, Monterrey",
        "interior_number": "Depto 3",
        "amount": Decimal("300.00"),
        "status": "pendiente",
        "collected_at": None,
        "abono_id": None,
    }


def test_confirm_inserts_abono_with_installment():
    repository = FakeCollectionsRepository()

    detail = make_service(repository).confirm(20, None)

    promise_id, amount, collected_at = repository.inserted
    assert (promise_id, amount) == (20, Decimal("300.00"))
    assert isinstance(collected_at, datetime)
    assert detail["status"] == "confirmada"
    assert detail["abono_id"] == 99
    assert detail["collected_at"] == collected_at.isoformat()


def test_confirm_uses_amount_from_body():
    repository = FakeCollectionsRepository()
    make_service(repository).confirm(20, Decimal("250.50"))
    assert repository.inserted[1] == Decimal("250.50")


@pytest.mark.parametrize(
    ("overrides", "status"),
    [
        ({"state": "cancelado"}, 409),
        (
            {
                "abono_hoy_id": 5,
                "abono_hoy_monto": Decimal("300"),
                "abono_hoy_fecha": datetime(2026, 10, 17),
            },
            409,
        ),
        ({"total_pagado": Decimal("3600.00")}, 409),
    ],
)
def test_confirm_rejections(overrides, status):
    repository = FakeCollectionsRepository({**ROW, **overrides})
    with pytest.raises(HttpException) as error:
        make_service(repository).confirm(20, None)
    assert error.value.status == status
    assert repository.inserted is None


def test_not_found():
    with pytest.raises(HttpException) as error:
        make_service(FakeCollectionsRepository(row=None)).get_collection(1)
    assert error.value.status == 404


def test_not_collected_cannot_be_saved_yet():
    with pytest.raises(HttpException) as error:
        make_service(FakeCollectionsRepository()).not_collected(20, "reprogramar")
    assert error.value.status == 501


def test_database_error_becomes_500():
    service = make_service(FakeCollectionsRepository(error=RuntimeError("db down")))
    with pytest.raises(HttpException) as error:
        service.get_collection(20)
    assert error.value.status == 500


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({}, Decimal("300.00")),
        ({"total_pagado": Decimal("3500.00")}, Decimal("100.00")),
        ({"numero_frequencia": None, "total_pagado": None}, Decimal("3600.00")),
    ],
)
def test_installment(overrides, expected):
    assert get_installment({**ROW, **overrides}) == expected


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
