import logging
from datetime import datetime, timedelta
from decimal import Decimal

from ...database import Database
from ...errors import HttpException
from .repository import (
    CallHistoryRow,
    DonationRow,
    DonorOptionRow,
    HistoryRepository,
    PromiseRow,
)

INTERNAL_ERROR = "Internal server error"

HISTORY_TYPES = ("all", "donations", "calls")

DAYS_PER_FREQUENCY = {
    "semanal": 7,
    "quincenal": 15,
    "mensual": 30,
    "bimestral": 60,
    "trimestral": 90,
    "semestral": 180,
    "anual": 365,
}

GREEN_RESULTS = ("confirmado",)
GRAY_RESULTS = ("no contesta", "incorrecto", "buzon", "buzón")

CENTS = Decimal("0.01")

log = logging.getLogger(__name__)


class HistoryService:
    def __init__(self, database: Database) -> None:
        self.history = HistoryRepository(database)

    def get_history(
        self,
        user_id: int,
        donor_id: int | None,
        history_type: str,
        search: str | None,
    ) -> list[dict]:
        records: list[dict] = []
        if history_type != "calls":
            records += self.get_donation_history(user_id, donor_id, search)
        if history_type != "donations":
            records += self.get_call_history(user_id, donor_id, search)
        return sort_by_date(records)

    def get_call_history(
        self, user_id: int, donor_id: int | None, search: str | None
    ) -> list[dict]:
        rows = self._query(
            "call history", self.history.find_calls, user_id, donor_id, search
        )
        return [to_public_call(row) for row in rows]

    def get_donation_history(
        self, user_id: int, donor_id: int | None, search: str | None
    ) -> list[dict]:
        donations = self._query(
            "donations", self.history.find_donations, user_id, donor_id, search
        )
        promises = self._query(
            "active promises",
            self.history.find_active_promises,
            user_id,
            donor_id,
            search,
        )

        today = datetime.now()
        records = [to_public_donation(row) for row in donations]
        records += [
            to_public_pending_payment(row, due_date)
            for row in promises
            if (due_date := get_overdue_date(row, today)) is not None
        ]
        return sort_by_date(records)

    def get_donors(self, user_id: int) -> list[dict]:
        rows = self._query("history donors", self.history.find_donors, user_id)
        return [to_public_donor(row) for row in rows]

    def _query(self, name: str, find, *args) -> list[dict]:
        try:
            return find(*args)
        except Exception as error:
            log.exception("Failed to fetch %s", name)
            raise HttpException(500, INTERNAL_ERROR) from error


def get_overdue_date(row: PromiseRow, today: datetime) -> datetime | None:
    days = DAYS_PER_FREQUENCY.get(row["tipo_frquencia"])
    if days is None:
        return None

    total_paid = row["total_pagado"] or Decimal(0)
    if total_paid >= row["monto_objetivo"]:
        return None

    due_date = (row["ultimo_pago"] or row["fecha_inicio"]) + timedelta(days=days)
    return due_date if due_date <= today else None


def to_public_donor(row: DonorOptionRow) -> dict:
    return {
        "donor_id": row["donor_id"],
        "name": row["nombre"],
        "last_name": row["apellido_paterno"],
        "mother_last_name": row["apellido_materno"],
    }


def to_public_call(row: CallHistoryRow) -> dict:
    return {
        "id": f"call-{row['call_id']}",
        "type": "call",
        **to_public_donor(row),
        "date": iso_date(row["fecha_agendada"]),
        "amount": row["monto_comprometido"],
        "status_color": get_call_color(row["call_status"], row["resultado_llamado"]),
        "call_status": row["call_status"],
        "purpose": row["proposito"],
        "result": row["resultado_llamado"],
        "is_paid": None,
    }


def to_public_donation(row: DonationRow) -> dict:
    return {
        "id": f"donation-{row['donation_id']}",
        "type": "donation",
        **to_public_donor(row),
        "date": iso_date(row["fecha_deposito"]),
        "amount": row["monto"],
        "status_color": "green",
        "call_status": None,
        "purpose": None,
        "result": None,
        "is_paid": True,
    }


def to_public_pending_payment(row: PromiseRow, due_date: datetime) -> dict:
    installment = row["monto_objetivo"] / row["numero_frequencia"]
    return {
        "id": f"pending-{row['promesa_id']}",
        "type": "donation",
        **to_public_donor(row),
        "date": iso_date(due_date),
        "amount": installment.quantize(CENTS),
        "status_color": "red",
        "call_status": None,
        "purpose": row["tipo_frquencia"],
        "result": None,
        "is_paid": False,
    }


def get_call_color(status: str, result: str | None) -> str:
    text = (result or "").lower()
    if status == "agendada":
        return "blue"
    if status == "cancelada" or any(word in text for word in GRAY_RESULTS):
        return "gray"
    if any(word in text for word in GREEN_RESULTS):
        return "green"
    return "orange"


def iso_date(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def sort_by_date(records: list[dict]) -> list[dict]:
    # ISO strings sort chronologically; records without a date go last.
    return sorted(records, key=lambda record: record["date"] or "", reverse=True)
