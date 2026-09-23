from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from caritas_backend.errors import HttpException
from caritas_backend.modules.historial.service import (
    HistoryService,
    get_call_color,
    get_overdue_date,
)

TODAY = datetime(2026, 9, 23)

DONOR = {
    "donor_id": 3,
    "nombre": "Alejandro",
    "apellido_paterno": "Torres",
    "apellido_materno": "Díaz",
}


class FakeHistoryRepository:
    def __init__(self, calls=(), donations=(), promises=(), donors=(), error=None):
        self.calls = list(calls)
        self.donations = list(donations)
        self.promises = list(promises)
        self.donors = list(donors)
        self.error = error
        self.received = []

    def find_calls(self, *args):
        return self._answer("calls", args, self.calls)

    def find_donations(self, *args):
        return self._answer("donations", args, self.donations)

    def find_active_promises(self, *args):
        return self._answer("promises", args, self.promises)

    def find_donors(self, *args):
        return self._answer("donors", args, self.donors)

    def _answer(self, name, args, rows):
        self.received.append((name, args))
        if self.error:
            raise self.error
        return rows


def make_service(repository):
    service = HistoryService.__new__(HistoryService)
    service.history = repository
    return service


def make_call(**overrides):
    return {
        **DONOR,
        "call_id": 7,
        "call_status": "completada",
        "proposito": "seguimiento",
        "resultado_llamado": "compromiso confirmado",
        "monto_comprometido": Decimal("500.00"),
        "fecha_agendada": datetime(2026, 8, 5),
        **overrides,
    }


def make_donation(**overrides):
    return {
        **DONOR,
        "donation_id": 12,
        "promesa_id": 4,
        "monto": Decimal("1200.00"),
        "fecha_deposito": datetime(2026, 5, 12),
        **overrides,
    }


def make_promise(**overrides):
    return {
        **DONOR,
        "promesa_id": 4,
        "monto_objetivo": Decimal("3600.00"),
        "fecha_inicio": datetime(2026, 1, 1),
        "numero_frequencia": 3,
        "tipo_frquencia": "mensual",
        "ultimo_pago": datetime(2026, 5, 12),
        "total_pagado": Decimal("1200.00"),
        **overrides,
    }


def test_maps_call_to_public_record():
    service = make_service(FakeHistoryRepository(calls=[make_call()]))

    assert service.get_call_history(1, None, None) == [
        {
            "id": "call-7",
            "type": "call",
            "donor_id": 3,
            "name": "Alejandro",
            "last_name": "Torres",
            "mother_last_name": "Díaz",
            "date": "2026-08-05T00:00:00",
            "amount": Decimal("500.00"),
            "status_color": "green",
            "call_status": "completada",
            "purpose": "seguimiento",
            "result": "compromiso confirmado",
            "is_paid": None,
        }
    ]


def test_passes_filters_to_repository():
    repository = FakeHistoryRepository()
    make_service(repository).get_call_history(1, 3, "ale")
    assert repository.received == [("calls", (1, 3, "ale"))]


def test_donations_include_paid_and_overdue_payments():
    repository = FakeHistoryRepository(
        donations=[make_donation()], promises=[make_promise()]
    )

    records = make_service(repository).get_donation_history(1, None, None)

    assert [(r["id"], r["is_paid"], r["status_color"]) for r in records] == [
        ("pending-4", False, "red"),
        ("donation-12", True, "green"),
    ]
    assert records[0]["amount"] == Decimal("1200.00")
    assert records[0]["date"] == "2026-06-11T00:00:00"


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({}, datetime(2026, 6, 11)),
        ({"ultimo_pago": None}, datetime(2026, 1, 31)),
        ({"ultimo_pago": TODAY - timedelta(days=5)}, None),
        ({"total_pagado": Decimal("3600.00")}, None),
        ({"tipo_frquencia": "desconocida"}, None),
    ],
)
def test_overdue_date(overrides, expected):
    assert get_overdue_date(make_promise(**overrides), TODAY) == expected


def test_history_filters_by_type_and_sorts_by_date():
    repository = FakeHistoryRepository(
        calls=[make_call(), make_call(call_id=8, fecha_agendada=None)],
        donations=[make_donation()],
    )
    service = make_service(repository)

    assert [r["id"] for r in service.get_history(1, None, "all", None)] == [
        "call-7",
        "donation-12",
        "call-8",
    ]
    assert [r["type"] for r in service.get_history(1, None, "calls", None)] == [
        "call",
        "call",
    ]
    assert [r["type"] for r in service.get_history(1, None, "donations", None)] == [
        "donation"
    ]


@pytest.mark.parametrize(
    ("status", "result", "color"),
    [
        ("completada", "compromiso confirmado", "green"),
        ("completada", "contactado", "orange"),
        ("completada", "no contesta", "gray"),
        ("completada", "numero incorrecto", "gray"),
        ("cancelada", "contactado", "gray"),
        ("agendada", "solicita volver a llamar", "blue"),
    ],
)
def test_call_color(status, result, color):
    assert get_call_color(status, result) == color


def test_donors_for_dropdown():
    service = make_service(FakeHistoryRepository(donors=[DONOR]))
    assert service.get_donors(1) == [
        {
            "donor_id": 3,
            "name": "Alejandro",
            "last_name": "Torres",
            "mother_last_name": "Díaz",
        }
    ]


def test_repository_error_becomes_500():
    service = make_service(FakeHistoryRepository(error=RuntimeError("db down")))
    with pytest.raises(HttpException) as error:
        service.get_history(1, None, "all", None)
    assert error.value.status == 500
