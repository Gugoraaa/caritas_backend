import logging
from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from ...database import Database
from ...errors import HttpException
from ..auth.guard import is_admin
from .repository import CallResultRow, CallRow, CallsRepository

INTERNAL_ERROR = "Internal server error"
CALL_NOT_FOUND = "Call not found"
CALL_FORBIDDEN = "You are not allowed to update this call"
CALL_ALREADY_REGISTERED = "Call is not scheduled; it was already registered"

# Estados con los que PATCH /calls/{id} puede cerrar una llamada; el default es
# el primero.
CALL_RESULT_STATES = ("completada", "cancelada")

DAYS_GREEN = 30
DAYS_YELLOW = 60

RESULT_PROMISE = "promesa de donativo"
RESULT_CALL_BACK = "volver a llamar"
RESULT_REJECTED = "rechazó"
RESULT_UNSUBSCRIBE = "solicitar baja"
RESULT_NO_ANSWER = "no contestó"
CALL_RESULTS = (
    RESULT_PROMISE,
    RESULT_CALL_BACK,
    RESULT_REJECTED,
    RESULT_UNSUBSCRIBE,
    RESULT_NO_ANSWER,
)
RESULTS_NEEDING_FOLLOW_UP = (RESULT_CALL_BACK, RESULT_NO_ANSWER)

STATUS_SCHEDULED = "agendada"
STATUS_COMPLETED = "completada"
PENDING_RESULT = "pendiente"

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

    def register_call(self, data: dict) -> dict:
        result = data["resultado"]
        notes = data.get("notas")
        amount = to_decimal(data.get("monto_comprometido"))
        follow_up = parse_follow_up(data.get("fecha_seguimiento"))

        if result == RESULT_PROMISE and (amount is None or not notes):
            raise HttpException(
                400, f"monto_comprometido and notas are required for '{result}'"
            )
        if result in RESULTS_NEEDING_FOLLOW_UP and follow_up is None:
            raise HttpException(400, f"fecha_seguimiento is required for '{result}'")

        try:
            call = self.calls.find_call(data["llamada_id"])
        except Exception as error:
            log.exception("Failed to fetch call")
            raise HttpException(500, INTERNAL_ERROR) from error

        if call is None:
            raise HttpException(404, CALL_NOT_FOUND)
        if call["estado"] != STATUS_SCHEDULED:
            raise HttpException(409, CALL_ALREADY_REGISTERED)

        status = STATUS_SCHEDULED if result == RESULT_NO_ANSWER else STATUS_COMPLETED
        update = {
            "resultado_llamado": result,
            "notas_llamada": notes,
            "estado": status,
            "monto_comprometido": amount,
            # Solo "no contestó" mueve esta misma llamada a la nueva fecha.
            "fecha_agendada": follow_up if result == RESULT_NO_ANSWER else None,
        }
        new_call = None
        if result == RESULT_CALL_BACK:
            new_call = build_follow_up_call(call, follow_up)
        new_promise = None
        if result == RESULT_PROMISE:
            new_promise = build_promise(call, amount, data["user_id"])

        try:
            saved = self.calls.register_result(
                call["id"], update, new_call, new_promise
            )
        except Exception as error:
            log.exception("Failed to register call result")
            raise HttpException(500, INTERNAL_ERROR) from error

        if saved is None:
            raise HttpException(409, CALL_ALREADY_REGISTERED)

        return {
            "llamada_id": call["id"],
            "estado": status,
            "resultado": result,
            "notas": notes,
            "fecha_agendada": iso_date(update["fecha_agendada"]),
            "nueva_llamada_id": saved["nueva_llamada_id"],
            "promesa_id": saved["promesa_id"],
        }


def build_follow_up_call(call: dict, follow_up: datetime) -> dict:
    return {
        "promesa_id": call["promesa_id"],
        "resultado_llamado": PENDING_RESULT,
        "monto_comprometido": call["monto_comprometido"],
        "estado": STATUS_SCHEDULED,
        "proposito": call["proposito"],
        "fecha_agendada": follow_up,
    }


def build_promise(call: dict, amount: Decimal, user_id: int) -> dict:
    return {
        "donante_id": call["donante_id"],
        "caso_id": call["caso_id"],
        "responsable_id": user_id,
        "monto_objetivo": amount,
        "state": "activo",
        "fecha_inicio": today_local(),
        "numero_frequencia": 1,
        "tipo_frquencia": "unica",
    }


def to_decimal(value: int | float | None) -> Decimal | None:
    # str() evita arrastrar el error binario del float (0.1 -> 0.1000000000000000055).
    return None if value is None else Decimal(str(value))


def parse_follow_up(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise HttpException(400, "fecha_seguimiento must be an ISO date") from error
    # La DB guarda hora local de Monterrey sin zona.
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(BUSINESS_TIMEZONE).replace(tzinfo=None)
    return parsed


def iso_date(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


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
