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
        call = self._find_scheduled_call(data["llamada_id"])
        new_call = None
        new_promise = None

        if result == RESULT_PROMISE:
            amount = to_decimal(require(data, "monto_comprometido"))
            require(data, "notas")
            follow_up = parse_follow_up(require(data, "fecha_seguimiento"))
            update = call_update(result, notes, STATUS_COMPLETED, amount=amount)
            new_promise = build_promise(call, amount, data["user_id"])
            new_call = build_follow_up_call(call, follow_up, None, amount)
        elif result == RESULT_CALL_BACK:
            follow_up = parse_follow_up(require(data, "fecha_seguimiento"))
            update = call_update(result, notes, STATUS_COMPLETED)
            new_call = build_follow_up_call(
                call, follow_up, call["promesa_id"], call["monto_comprometido"]
            )
        elif result == RESULT_NO_ANSWER:
            # Esta misma llamada sigue agendada y se mueve a la nueva fecha.
            follow_up = parse_follow_up(require(data, "fecha_seguimiento"))
            update = call_update(
                result, notes, STATUS_SCHEDULED, scheduled_at=follow_up
            )
        elif result in (RESULT_REJECTED, RESULT_UNSUBSCRIBE):
            # Solo se guardan el resultado y las notas.
            update = call_update(result, notes, STATUS_COMPLETED)

        self._save(call["id"], update, new_call, new_promise)
        return {"message": "ok"}

    def _find_scheduled_call(self, call_id: int) -> dict:
        try:
            call = self.calls.find_call(call_id)
        except Exception as error:
            log.exception("Failed to fetch call")
            raise HttpException(500, INTERNAL_ERROR) from error

        if call is None:
            raise HttpException(404, CALL_NOT_FOUND)
        if call["estado"] != STATUS_SCHEDULED:
            raise HttpException(409, CALL_ALREADY_REGISTERED)
        return call

    def _save(
        self,
        call_id: int,
        update: dict,
        new_call: dict | None,
        new_promise: dict | None,
    ) -> None:
        try:
            saved = self.calls.register_result(call_id, update, new_call, new_promise)
        except Exception as error:
            log.exception("Failed to register call result")
            raise HttpException(500, INTERNAL_ERROR) from error

        if not saved:
            raise HttpException(409, CALL_ALREADY_REGISTERED)


def require(data: dict, field: str):
    value = data.get(field)
    if value is None or value == "":
        raise HttpException(400, f"{field} is required for '{data['resultado']}'")
    return value


def call_update(
    result: str,
    notes: str | None,
    status: str,
    amount: Decimal | None = None,
    scheduled_at: datetime | None = None,
) -> dict:
    return {
        "resultado_llamado": result,
        "notas_llamada": notes,
        "estado": status,
        "monto_comprometido": amount,
        "fecha_agendada": scheduled_at,
    }


def build_follow_up_call(
    call: dict, follow_up: datetime, promise_id: int | None, amount: Decimal | None
) -> dict:
    return {
        "promesa_id": promise_id,
        "resultado_llamado": PENDING_RESULT,
        "monto_comprometido": amount,
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


def to_decimal(value: int | float) -> Decimal:
    # str() evita arrastrar el error binario del float (0.1 -> 0.1000000000000000055).
    return Decimal(str(value))


def parse_follow_up(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise HttpException(400, "fecha_seguimiento must be an ISO date") from error
    # La DB guarda hora local de Monterrey sin zona.
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(BUSINESS_TIMEZONE).replace(tzinfo=None)
    return parsed


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
