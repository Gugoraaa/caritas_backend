from datetime import datetime
from decimal import Decimal

import pytest

from caritas_backend.errors import HttpException
from caritas_backend.modules.llamadas.controller import UPDATE_RULES
from caritas_backend.modules.llamadas.service import CallsService
from caritas_backend.validation import check

ADMIN = {"userId": 7, "role": "admin"}
OWNER = {"userId": 2, "role": "promotor"}
STRANGER = {"userId": 3, "role": "promotor"}

RESULT_ROW = {
    "call_id": 5,
    "donor_id": 11,
    "call_status": "completada",
    "fecha_agendada": datetime(2026, 10, 17, 12, 0),
    "proposito": "seguimiento",
    "resultado_llamado": "contactado",
    "monto_comprometido": Decimal("250.00"),
}


class FakeCallsRepository:
    def __init__(self, owner=None, affected=1, error=None):
        self.owner = owner
        self.affected = affected
        self.error = error
        self.updates = []

    def find_owner(self, call_id):
        if self.error:
            raise self.error
        return self.owner

    def update(self, call_id, data):
        self.updates.append((call_id, data))
        return self.affected

    def find_result(self, call_id):
        return RESULT_ROW


def make_service(repository):
    service = CallsService.__new__(CallsService)
    service.calls = repository
    return service


def owned_by(user_id):
    return FakeCallsRepository(owner={"call_id": 5, "responsable_id": user_id})


def test_owner_records_result_with_default_state():
    repository = owned_by(2)
    result = make_service(repository).record_result(
        5, {"resultado_llamado": "contactado"}, OWNER
    )

    assert repository.updates == [
        (5, {"resultado_llamado": "contactado", "estado": "completada"})
    ]
    assert result == {
        "call_id": 5,
        "donor_id": 11,
        "call_status": "completada",
        "scheduled_date": "2026-10-17T12:00:00",
        "purpose": "seguimiento",
        "result": "contactado",
        "amount": Decimal("250.00"),
    }


def test_explicit_state_and_null_fields_are_sent():
    repository = owned_by(2)
    body = {"resultado_llamado": "x", "estado": "cancelada", "proposito": None}
    make_service(repository).record_result(5, body, OWNER)
    assert repository.updates == [(5, body)]


@pytest.mark.parametrize("role", ["admin", "Admin", "ADMIN"])
def test_admin_can_update_any_call(role):
    repository = owned_by(None)
    user = {**ADMIN, "role": role}
    make_service(repository).record_result(5, {"resultado_llamado": "x"}, user)
    assert len(repository.updates) == 1


@pytest.mark.parametrize(
    ("repository", "user", "status"),
    [
        (FakeCallsRepository(owner=None), ADMIN, 404),
        (owned_by(2), STRANGER, 403),
        (owned_by(None), OWNER, 403),
        (FakeCallsRepository(error=RuntimeError("db down")), ADMIN, 500),
    ],
)
def test_errors(repository, user, status):
    with pytest.raises(HttpException) as error:
        make_service(repository).record_result(5, {"resultado_llamado": "x"}, user)
    assert error.value.status == status
    assert repository.updates == []


@pytest.mark.parametrize(
    ("body", "messages"),
    [
        (
            {},
            [
                "resultado_llamado should not be empty",
                "resultado_llamado must be a string",
            ],
        ),
        (
            {"resultado_llamado": "x", "proposito": "p" * 31},
            ["proposito must be shorter than or equal to 30 characters"],
        ),
        (
            {"resultado_llamado": "x", "monto_comprometido": -1},
            ["monto_comprometido must not be less than 0"],
        ),
        (
            {"resultado_llamado": "x", "monto_comprometido": True},
            [
                "monto_comprometido must be a number",
                "monto_comprometido must not be less than 0",
            ],
        ),
        (
            {"resultado_llamado": "x", "estado": "agendada"},
            ["estado must be one of ['completada', 'cancelada']"],
        ),
    ],
)
def test_update_validation(body, messages):
    with pytest.raises(HttpException) as error:
        check(UPDATE_RULES, body)
    assert error.value.status == 400
    assert error.value.message == messages


def test_update_validation_keeps_only_declared_fields():
    body = {"resultado_llamado": "x", "monto_comprometido": 0, "id": 99}
    assert check(UPDATE_RULES, body) == {
        "resultado_llamado": "x",
        "monto_comprometido": 0,
    }
