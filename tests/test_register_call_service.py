from datetime import datetime
from decimal import Decimal

import pytest

from caritas_backend.errors import HttpException
from caritas_backend.modules.llamadas.service import CallsService

CALL = {
    "id": 7,
    "promesa_id": 3,
    "estado": "agendada",
    "monto_comprometido": Decimal("500.00"),
    "proposito": "seguimiento",
    "donante_id": 11,
    "caso_id": 4,
}


class FakeCallsRepository:
    def __init__(self, call=CALL, saved=True, error=None):
        self.call = call
        self.saved = saved
        self.error = error
        self.registered = None

    def find_call(self, call_id):
        if self.error:
            raise self.error
        return self.call

    def register_result(self, call_id, update, new_call, new_promise):
        self.registered = (call_id, update, new_call, new_promise)
        return self.saved


def make_service(repository):
    service = CallsService.__new__(CallsService)
    service.calls = repository
    return service


def body(**overrides):
    return {"llamada_id": 7, "user_id": 2, **overrides}


@pytest.mark.parametrize("result", ["rechazó", "solicitar baja"])
def test_closing_results_complete_the_call_without_side_effects(result):
    repository = FakeCallsRepository()
    response = make_service(repository).register_call(
        body(resultado=result, notas="no le interesa")
    )

    _, update, new_call, new_promise = repository.registered
    assert update["estado"] == "completada"
    assert update["resultado_llamado"] == result
    assert update["notas_llamada"] == "no le interesa"
    assert update["fecha_agendada"] is None
    assert new_call is None
    assert new_promise is None
    assert response == {"message": "ok"}


def test_no_answer_keeps_call_scheduled_and_moves_its_date():
    repository = FakeCallsRepository()
    make_service(repository).register_call(
        body(resultado="no contestó", fecha_seguimiento="2026-10-20T10:00:00")
    )

    _, update, new_call, _ = repository.registered
    assert update["estado"] == "agendada"
    assert update["fecha_agendada"] == datetime(2026, 10, 20, 10, 0)
    assert new_call is None


def test_call_back_completes_call_and_schedules_a_copy():
    repository = FakeCallsRepository()
    make_service(repository).register_call(
        body(resultado="volver a llamar", fecha_seguimiento="2026-10-20")
    )

    _, update, new_call, _ = repository.registered
    assert update["estado"] == "completada"
    assert update["fecha_agendada"] is None
    assert new_call == {
        "promesa_id": 3,
        "resultado_llamado": "pendiente",
        "monto_comprometido": Decimal("500.00"),
        "estado": "agendada",
        "proposito": "seguimiento",
        "fecha_agendada": datetime(2026, 10, 20),
    }


def promise_body(**overrides):
    return body(
        resultado="promesa de donativo",
        monto_comprometido=1250.5,
        notas="ok",
        fecha_seguimiento="2026-11-03",
        **overrides,
    )


def test_promise_creates_a_single_payment_promise_for_the_user():
    repository = FakeCallsRepository()
    make_service(repository).register_call(promise_body())

    _, update, _, new_promise = repository.registered
    assert update["estado"] == "completada"
    assert update["monto_comprometido"] == Decimal("1250.5")
    assert new_promise["donante_id"] == 11
    assert new_promise["caso_id"] == 4
    assert new_promise["responsable_id"] == 2
    assert new_promise["monto_objetivo"] == Decimal("1250.5")
    assert new_promise["state"] == "activo"
    assert new_promise["numero_frequencia"] == 1
    assert new_promise["tipo_frquencia"] == "unica"


def test_promise_schedules_a_call_linked_to_the_new_promise():
    repository = FakeCallsRepository()
    make_service(repository).register_call(promise_body())

    _, update, new_call, _ = repository.registered
    assert update["fecha_agendada"] is None
    assert new_call == {
        # None = el repositorio usa el id de la promesa recien creada.
        "promesa_id": None,
        "resultado_llamado": "pendiente",
        "monto_comprometido": Decimal("1250.5"),
        "estado": "agendada",
        "proposito": "seguimiento",
        "fecha_agendada": datetime(2026, 11, 3),
    }


@pytest.mark.parametrize(
    "missing",
    ["notas", "monto_comprometido", "fecha_seguimiento"],
)
def test_promise_requires_amount_notes_and_date(missing):
    data = promise_body()
    del data[missing]
    with pytest.raises(HttpException) as error:
        make_service(FakeCallsRepository()).register_call(data)
    assert error.value.status == 400


@pytest.mark.parametrize(
    "result", ["promesa de donativo", "volver a llamar", "no contestó"]
)
def test_follow_up_results_require_a_date(result):
    with pytest.raises(HttpException) as error:
        make_service(FakeCallsRepository()).register_call(body(resultado=result))
    assert error.value.status == 400


def test_invalid_follow_up_date_is_rejected():
    with pytest.raises(HttpException) as error:
        make_service(FakeCallsRepository()).register_call(
            body(resultado="no contestó", fecha_seguimiento="mañana")
        )
    assert error.value.status == 400


def test_missing_call_returns_404():
    with pytest.raises(HttpException) as error:
        make_service(FakeCallsRepository(call=None)).register_call(
            body(resultado="rechazó")
        )
    assert error.value.status == 404


def test_already_registered_call_returns_409():
    repository = FakeCallsRepository(call={**CALL, "estado": "completada"})
    with pytest.raises(HttpException) as error:
        make_service(repository).register_call(body(resultado="rechazó"))
    assert error.value.status == 409
    assert repository.registered is None


def test_call_registered_concurrently_returns_409():
    repository = FakeCallsRepository(saved=False)
    with pytest.raises(HttpException) as error:
        make_service(repository).register_call(body(resultado="rechazó"))
    assert error.value.status == 409


def test_database_error_returns_500():
    repository = FakeCallsRepository(error=RuntimeError("db down"))
    with pytest.raises(HttpException) as error:
        make_service(repository).register_call(body(resultado="rechazó"))
    assert error.value.status == 500
