import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from ...database import Database
from ...errors import HttpException
from ..auth.guard import is_admin
from .repository import CallResultRow, CallRow, CallsRepository

INTERNAL_ERROR = "Internal server error"
CALL_NOT_FOUND = "Call not found"
CALL_FORBIDDEN = "You are not allowed to update this call"

# Estados con los que se puede cerrar una llamada; el default es el primero.
CALL_RESULT_STATES = ("completada", "cancelada")

DAYS_GREEN = 30
DAYS_YELLOW = 60

# Monterrey es UTC-6 todo el anio (sin horario de verano desde 2022).
# El servidor corre en UTC: sin esto, la ventana de "hoy" se voltea a las
# 18:00 hora local y la pantalla se vacia todas las noches.
BUSINESS_TIMEZONE = ZoneInfo("America/Monterrey")

log = logging.getLogger(__name__)


class CallsService:
    def __init__(self, database: Database) -> None:
        self.calls = CallsRepository(database)

    def get_scheduled_today_tomorrow(self, user_id: int) -> list[dict]:
        today = today_local()
        tomorrow_end = today + timedelta(days=2)

        try:
            rows = self.calls.find_scheduled_between(user_id, today, tomorrow_end)
        except Exception as error:
            log.exception("Failed to fetch scheduled calls")
            raise HttpException(500, INTERNAL_ERROR) from error

        return [to_public_call(row, today) for row in rows]

    def record_result(self, call_id: int, data: dict, user: dict) -> dict:
        owner = self._query("call owner", self.calls.find_owner, call_id)
        if owner is None:
            raise HttpException(404, CALL_NOT_FOUND)
        if not is_admin(user["role"]) and owner["responsable_id"] != user["userId"]:
            raise HttpException(403, CALL_FORBIDDEN)

        changes = {**data, "estado": data.get("estado") or CALL_RESULT_STATES[0]}
        affected = self._query("call update", self.calls.update, call_id, changes)
        if affected == 0:
            raise HttpException(404, CALL_NOT_FOUND)

        row = self._query("call result", self.calls.find_result, call_id)
        if row is None:
            raise HttpException(404, CALL_NOT_FOUND)
        return to_public_result(row)

    def _query(self, name: str, run, *args):
        try:
            return run(*args)
        except Exception as error:
            log.exception("Failed to run %s", name)
            raise HttpException(500, INTERNAL_ERROR) from error


def today_local(now: datetime | None = None) -> datetime:
    """Medianoche de hoy en Monterrey, como datetime naive (igual que la DB)."""
    current = now if now is not None else datetime.now(BUSINESS_TIMEZONE)
    return current.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)


def to_public_call(row: CallRow, today: datetime) -> dict:
    latest_payment_date = row["latest_payment_date"]
    days_since_last_payment = (
        (today - latest_payment_date).days if latest_payment_date else None
    )

    return {
        "donor_id": row["donor_id"],
        "name": row["nombre"],
        "last_name": row["apellido_paterno"],
        "mother_last_name": row["apellido_materno"],
        "call_id": row["call_id"],
        "call_status": row["call_status"],
        "scheduled_date": row["fecha_agendada"].isoformat(),
        "days_since_last_payment": days_since_last_payment,
        "latest_payment_amount": row["latest_payment_amount"],
        "status_color": get_color(days_since_last_payment),
    }


def to_public_result(row: CallResultRow) -> dict:
    scheduled = row["fecha_agendada"]
    return {
        "call_id": row["call_id"],
        "donor_id": row["donor_id"],
        "call_status": row["call_status"],
        "scheduled_date": scheduled.isoformat() if scheduled else None,
        "purpose": row["proposito"],
        "result": row["resultado_llamado"],
        "amount": row["monto_comprometido"],
    }


def get_color(days: int | None) -> str:
    if days is not None and days < DAYS_GREEN:
        return "green"
    if days is not None and days < DAYS_YELLOW:
        return "yellow"
    return "red"
