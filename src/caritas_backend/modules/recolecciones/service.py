import logging
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from ...database import Database
from ...errors import HttpException
from .repository import CollectionRow, CollectionsRepository

INTERNAL_ERROR = "Internal server error"
NOT_FOUND = "Collection not found"
NOT_PENDING = "Collection is not pending; it was already resolved"
INVALID_RANGE = "from must be on or before to"

STATUS_PENDING = "pendiente"
STATUS_CONFIRMED = "confirmada"
STATUS_NOT_COLLECTED = "no_recolectada"

NOT_COLLECTED_REASONS = {
    "nadie_en_domicilio": "No había nadie en el domicilio",
    "reprogramar": "El donante pidió reprogramar",
    "domicilio_incorrecto": "Domicilio incorrecto",
    "ya_no_desea_donar": "El donante ya no desea donar",
}

# La DB guarda hora local de Monterrey sin zona (UTC-6, sin horario de verano).
BUSINESS_TIMEZONE = ZoneInfo("America/Monterrey")

log = logging.getLogger(__name__)


class CollectionsService:
    def __init__(self, database: Database) -> None:
        self.collections = CollectionsRepository(database)

    def get_collection(self, collection_id: int) -> dict:
        return to_public_collection(self._find(collection_id))

    def get_history(
        self, user_id: int, date_from: date | None, date_to: date | None
    ) -> list[dict]:
        """Recolecciones resueltas por el usuario; las fechas son dias inclusivos."""
        if date_from and date_to and date_from > date_to:
            raise HttpException(400, INVALID_RANGE)

        since = datetime.combine(date_from, time.min) if date_from else None
        until = datetime.combine(date_to + timedelta(days=1), time.min) if date_to else None
        try:
            rows = self.collections.find_history(user_id, since, until)
        except Exception as error:
            log.exception("Failed to fetch collection history")
            raise HttpException(500, INTERNAL_ERROR) from error
        return [to_public_history_item(row) for row in rows]

    def confirm(self, collection_id: int, user_id: int) -> dict:
        row = self._find_pending(collection_id)
        collected_at = now_local()

        try:
            abono_id = self.collections.confirm(
                collection_id, row["promesa_id"], row["monto"], collected_at, user_id
            )
        except Exception as error:
            log.exception("Failed to confirm collection")
            raise HttpException(500, INTERNAL_ERROR) from error

        if abono_id is None:
            raise HttpException(409, NOT_PENDING)

        return to_public_collection(
            {
                **row,
                "estado": STATUS_CONFIRMED,
                "fecha_resultado": collected_at,
                "abono_id": abono_id,
            }
        )

    def not_collected(self, collection_id: int, reason: str, user_id: int) -> dict:
        row = self._find_pending(collection_id)
        resolved_at = now_local()

        try:
            updated = self.collections.mark_not_collected(
                collection_id, reason, resolved_at, user_id
            )
        except Exception as error:
            log.exception("Failed to save not-collected reason")
            raise HttpException(500, INTERNAL_ERROR) from error

        if not updated:
            raise HttpException(409, NOT_PENDING)

        return to_public_collection(
            {
                **row,
                "estado": STATUS_NOT_COLLECTED,
                "motivo": reason,
                "fecha_resultado": resolved_at,
            }
        )

    def _find_pending(self, collection_id: int) -> CollectionRow:
        row = self._find(collection_id)
        if row["estado"] != STATUS_PENDING:
            raise HttpException(409, NOT_PENDING)
        return row

    def _find(self, collection_id: int) -> CollectionRow:
        try:
            row = self.collections.find(collection_id)
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


def format_address(row: CollectionRow) -> str | None:
    street = " ".join(part for part in (row["calle"], row["numero_exterior"]) if part)
    colonia = f"Col. {row['colonia']}" if row["colonia"] else None
    parts = [part for part in (street, colonia, row["municipio"]) if part]
    return ", ".join(parts) or None


def to_public_collection(row: CollectionRow) -> dict:
    reason = row["motivo"]
    return {
        "id": row["id"],
        "promise_id": row["promesa_id"],
        "donor_id": row["donor_id"],
        "name": row["nombre"],
        "last_name": row["apellido_paterno"],
        "mother_last_name": row["apellido_materno"],
        "phone": row["telefono"],
        "address": format_address(row),
        "interior_number": row["numero_interior"],
        "address_notes": row["notas_domicilio"],
        "scheduled_at": iso_date(row["fecha_programada"]),
        "window_start": iso_date(row["ventana_inicio"]),
        "window_end": iso_date(row["ventana_fin"]),
        "amount": row["monto"],
        "status": row["estado"],
        "reason": reason,
        "reason_label": NOT_COLLECTED_REASONS.get(reason) if reason else None,
        "resolved_at": iso_date(row["fecha_resultado"]),
        "abono_id": row["abono_id"],
    }


def to_public_history_item(row: CollectionRow) -> dict:
    return {
        "id": row["id"],
        "name": row["nombre"],
        "last_name": row["apellido_paterno"],
        "mother_last_name": row["apellido_materno"],
        "date": iso_date(row["updated_at"]),
        "status": row["estado"],
        "amount": row["monto_recolectado"],
    }


def iso_date(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def now_local() -> datetime:
    return datetime.now(BUSINESS_TIMEZONE).replace(microsecond=0, tzinfo=None)
