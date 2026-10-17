import logging
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from ...database import Database
from ...errors import HttpException
from .repository import CollectionRow, CollectionsRepository

INTERNAL_ERROR = "Internal server error"
NOT_FOUND = "Collection not found"
NOT_ACTIVE = "Promise is not active"
ALREADY_CONFIRMED = "Collection was already confirmed today"
FULLY_PAID = "Promise is already fully paid"
CANNOT_SAVE_REASON = (
    "Reason is valid but cannot be saved yet: the database has no table for collections"
)

STATUS_PENDING = "pendiente"
STATUS_CONFIRMED = "confirmada"
ACTIVE = "activo"

NOT_COLLECTED_REASONS = {
    "nadie_en_domicilio": "No había nadie en el domicilio",
    "reprogramar": "El donante pidió reprogramar",
    "domicilio_incorrecto": "Domicilio incorrecto",
    "ya_no_desea_donar": "El donante ya no desea donar",
}

CENTS = Decimal("0.01")

# La DB guarda hora local de Monterrey sin zona (UTC-6, sin horario de verano).
BUSINESS_TIMEZONE = ZoneInfo("America/Monterrey")

log = logging.getLogger(__name__)


class CollectionsService:
    def __init__(self, database: Database) -> None:
        self.collections = CollectionsRepository(database)

    def get_collection(self, promise_id: int) -> dict:
        return to_public_collection(self._find(promise_id))

    def confirm(self, promise_id: int, amount: Decimal | None) -> dict:
        row = self._find(promise_id)
        if row["state"] != ACTIVE:
            raise HttpException(409, NOT_ACTIVE)
        if row["abono_hoy_id"] is not None:
            raise HttpException(409, ALREADY_CONFIRMED)

        amount = amount if amount is not None else get_installment(row)
        if amount <= 0:
            raise HttpException(409, FULLY_PAID)

        collected_at = now_local()
        try:
            abono_id = self.collections.insert_abono(promise_id, amount, collected_at)
        except Exception as error:
            log.exception("Failed to confirm collection")
            raise HttpException(500, INTERNAL_ERROR) from error

        row = {
            **row,
            "abono_hoy_id": abono_id,
            "abono_hoy_monto": amount,
            "abono_hoy_fecha": collected_at,
        }
        return to_public_collection(row)

    def not_collected(self, promise_id: int, reason: str) -> dict:
        self._find(promise_id)
        # Sin tabla de recolecciones no hay donde guardar el motivo.
        raise HttpException(501, CANNOT_SAVE_REASON)

    def _find(self, promise_id: int) -> CollectionRow:
        try:
            row = self.collections.find(promise_id, today_local())
        except Exception as error:
            log.exception("Failed to fetch collection")
            raise HttpException(500, INTERNAL_ERROR) from error
        if row is None:
            raise HttpException(404, NOT_FOUND)
        return row


def get_reasons() -> list[dict]:
    return [
        {"code": code, "label": label} for code, label in NOT_COLLECTED_REASONS.items()
    ]


def get_installment(row: CollectionRow) -> Decimal:
    """Cuota de la promesa, sin pasarse de lo que falta por pagar."""
    payments = row["numero_frequencia"] or 1
    installment = row["monto_objetivo"] / max(payments, 1)
    remaining = row["monto_objetivo"] - (row["total_pagado"] or Decimal(0))
    return max(min(installment, remaining), Decimal(0)).quantize(CENTS)


def format_address(row: CollectionRow) -> str | None:
    street = " ".join(part for part in (row["calle"], row["numero_exterior"]) if part)
    colonia = f"Col. {row['colonia']}" if row["colonia"] else None
    parts = [part for part in (street, colonia, row["municipio"]) if part]
    return ", ".join(parts) or None


def to_public_collection(row: CollectionRow) -> dict:
    confirmed = row["abono_hoy_id"] is not None
    return {
        "promise_id": row["promesa_id"],
        "donor_id": row["donor_id"],
        "name": row["nombre"],
        "last_name": row["apellido_paterno"],
        "mother_last_name": row["apellido_materno"],
        "phone": row["telefono"],
        "address": format_address(row),
        "interior_number": row["numero_interior"],
        "amount": row["abono_hoy_monto"] if confirmed else get_installment(row),
        "status": STATUS_CONFIRMED if confirmed else STATUS_PENDING,
        "collected_at": iso_date(row["abono_hoy_fecha"]) if confirmed else None,
        "abono_id": row["abono_hoy_id"],
    }


def iso_date(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def now_local() -> datetime:
    return datetime.now(BUSINESS_TIMEZONE).replace(microsecond=0, tzinfo=None)


def today_local() -> datetime:
    return now_local().replace(hour=0, minute=0, second=0)
