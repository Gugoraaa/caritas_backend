from datetime import timedelta

import pytest

from caritas_backend.errors import HttpException
from caritas_backend.modules.llamadas.service import (
    PENDING_RESULT,
    STATUS_SCHEDULED,
    CallsService,
    today_local,
)


class FakeCallsRepository:
    def __init__(self, promise_ids):
        self.promise_ids = promise_ids
        self.inserted = []

    def find_active_promise_ids(self, user_id):
        return self.promise_ids

    def insert_calls(self, rows):
        self.inserted.extend(rows)


def make_service(promise_ids):
    service = CallsService(database=None)
    service.calls = FakeCallsRepository(promise_ids)
    return service


def test_seed_inserts_five_pending_calls_for_today_on_distinct_promises():
    service = make_service(list(range(1, 11)))

    assert service.seed_pending_today(7) == {"inserted": 5}

    rows = service.calls.inserted
    today = today_local()
    assert len({row["promesa_id"] for row in rows}) == 5
    for row in rows:
        assert row["estado"] == STATUS_SCHEDULED
        assert row["resultado_llamado"] == PENDING_RESULT
        assert (
            today + timedelta(hours=9)
            <= row["fecha_agendada"]
            <= today + timedelta(hours=18)
        )


def test_seed_uses_all_promises_when_user_has_fewer_than_five():
    service = make_service([3, 4])

    assert service.seed_pending_today(7) == {"inserted": 2}


def test_seed_without_active_promises_is_409():
    service = make_service([])

    with pytest.raises(HttpException) as error:
        service.seed_pending_today(7)

    assert error.value.status == 409
