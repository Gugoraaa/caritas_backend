from datetime import date, datetime
from decimal import Decimal

import pytest
from flask import Flask

from caritas_backend.errors import HttpException, register_error_handlers
from caritas_backend.modules.admin_resumen.controller import blueprint
from caritas_backend.modules.admin_resumen.service import AdminResumenService
from caritas_backend.modules.auth.service import AuthService
from caritas_backend.security import sign_token


class FakeRepository:
    def donations(self, start, end):
        assert (start, end) == (date(2026, 10, 1), date(2026, 11, 1))
        return [
            {"day": date(2026, 10, 2), "total": Decimal("10.50")},
            {"day": date(2026, 10, 5), "total": Decimal("2.00")},
        ]

    def outcomes(self):
        return [{"outcome": "promesa", "call_count": 2}]

    def calls_by_responsible(self):
        return [{"user_id": 7, "user_name": "Ana", "call_count": 3, "promise_count": 2}]

    def latest_donations(self):
        return [
            {"latest_donation": date(2026, 9, 17)},
            {"latest_donation": date(2026, 8, 18)},
            {"latest_donation": None},
        ]


def service(repository=None):
    result = AdminResumenService.__new__(AdminResumenService)
    result.repository = repository or FakeRepository()
    return result


def test_summary_totals_weeks_and_risk_boundaries():
    result = service().get_summary(datetime(2026, 10, 17))
    assert result["fundraising"]["total"] == Decimal("12.50")
    assert result["fundraising"]["weekly_totals"] == [
        {"start": "2026-10-01", "end": "2026-10-04", "total": Decimal("10.50")},
        {"start": "2026-10-05", "end": "2026-10-11", "total": Decimal("2.00")},
        {"start": "2026-10-12", "end": "2026-10-18", "total": 0},
        {"start": "2026-10-19", "end": "2026-10-25", "total": 0},
        {"start": "2026-10-26", "end": "2026-10-31", "total": 0},
    ]
    assert result["donor_risk"] == {"green": 0, "yellow": 1, "red": 2}


class FakeUsers:
    def find_by_id(self, user_id):
        role = {1: "admin", 2: "coordinador"}.get(user_id)
        return {"id": user_id, "role": role} if role else None


class FailingRepository(FakeRepository):
    def donations(self, start, end):
        raise RuntimeError("database down")


@pytest.fixture
def client():
    app = Flask(__name__)
    app.secret_key = "unused"
    auth = AuthService(None, "test-secret-that-is-at-least-32-bytes", 3600)
    auth.users = FakeUsers()
    app.extensions["auth"] = auth
    app.extensions["admin_resumen"] = service()
    register_error_handlers(app)
    app.register_blueprint(blueprint)
    return app.test_client()


def bearer(user_id):
    token = sign_token(
        {"userId": user_id}, "test-secret-that-is-at-least-32-bytes", 3600
    )
    return {"Authorization": f"Bearer {token}"}


def test_endpoint_serializes_and_requires_admin(client):
    response = client.get("/admin/summary", headers=bearer(1))
    assert response.status_code == 200
    assert response.get_json()["fundraising"]["total"] == "12.50"
    assert response.get_json()["call_outcomes"][0]["call_count"] == 2


def test_endpoint_auth_errors(client):
    assert client.get("/admin/summary").status_code == 401
    assert client.get("/admin/summary", headers=bearer(2)).status_code == 403


def test_database_errors_become_http_500():
    with pytest.raises(HttpException) as error:
        service(FailingRepository()).get_summary(datetime(2026, 10, 17))
    assert error.value.status == 500
