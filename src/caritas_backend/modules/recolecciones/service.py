import logging
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from ...database import Database
from ...errors import HttpException
from .repository import CollectionRow, CollectionsRepository

INTERNAL_ERROR = "Internal server error"
NOT_FOUND = "Collection not found"
NOT_PENDING = "Collection is not pending; it was already resolved"
NOT_OWNER = "Collection is assigned to another collector"
INVALID_RANGE = "from must be on or before to"

STATUS_PENDING = "pendiente"
STATUS_CONFIRMED = "confirmada"
STATUS_NOT_COLLECTED = "no_recolectada"
STATUSES = (STATUS_PENDING, STATUS_CONFIRMED, STATUS_NOT_COLLECTED)

NOT_COLLECTED_REASONS = {
    "nadie_en_domicilio": "No había nadie en el domicilio",
    "reprogramar": "El donante pidió reprogramar",
    "domicilio_incorrecto": "Domicilio incorrecto",
    "ya_no_desea_donar": "El donante ya no desea donar",
}

UPDATE_FIELDS = {
    "collector_id": "recolector_id",
    "scheduled_at": "fecha_programada",
    "window_start": "ventana_inicio",
    "window_end": "ventana_fin",
    "amount": "monto",
    "address_notes": "notas_domicilio",
}

# La DB guarda hora local de Monterrey sin zona (UTC-6, sin horario de verano).
BUSINESS_TIMEZONE = ZoneInfo("America/Monterrey")

log = logging.getLogger(__name__)


class CollectionsService:
    def __init__(self, database: Database) -> None:
        self.collections = CollectionsRepository(database)

    def get_collection(self, collection_id: int, owner_id: int | None = None) -> dict:
        return to_public_collection(self._find(collection_id, owner_id))

    def list_collections(
        self,
        status: str | None,
        collector_id: int | None,
        date_from: date | None,
        date_to: date | None,
    ) -> list[dict]:
        """Todas las recolecciones; las fechas (dia inclusivo) filtran fecha_programada."""
        if status is not None and status not in STATUSES:
            raise HttpException(400, f"status must be one of {list(STATUSES)}")
        if date_from and date_to and date_from > date_to:
            raise HttpException(400, INVALID_RANGE)

        since = datetime.combine(date_from, time.min) if date_from else None
        until = datetime.combine(date_to + timedelta(days=1), time.min) if date_to else None
        try:
            rows = self.collections.find_all(status, collector_id, since, until)
        except Exception as error:
            log.exception("Failed to list collections")
            raise HttpException(500, INTERNAL_ERROR) from error
        return [to_public_collection(row) for row in rows]

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

    def confirm(
        self, collection_id: int, user_id: int, owner_id: int | None = None
    ) -> dict:
        row = self._find_pending(collection_id, owner_id)
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

    def not_collected(
        self, collection_id: int, reason: str, user_id: int, owner_id: int | None = None
    ) -> dict:
        row = self._find_pending(collection_id, owner_id)
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

    def update(self, collection_id: int, fields: dict) -> dict:
        """Edita una recoleccion pendiente; fields usa los nombres publicos."""
        if not fields:
            raise HttpException(400, "At least one field is required")
        columns = {UPDATE_FIELDS[name]: value for name, value in fields.items()}
        for column in ("fecha_programada", "ventana_inicio", "ventana_fin"):
            if columns.get(column) is not None:
                columns[column] = parse_datetime(columns[column], column)
        if columns.get("monto") is not None and columns["monto"] <= 0:
            raise HttpException(400, "amount must be greater than 0")
        if columns.get("fecha_programada", True) is None or columns.get("monto", True) is None:
            raise HttpException(400, "scheduled_at and amount cannot be null")

        self._find_pending(collection_id)
        try:
            updated = self.collections.update_pending(collection_id, columns)
        except Exception as error:
            log.exception("Failed to update collection")
            raise HttpException(500, INTERNAL_ERROR) from error
        if not updated:
            raise HttpException(409, NOT_PENDING)
        return self.get_collection(collection_id)

    def delete(self, collection_id: int) -> None:
        self._find_pending(collection_id)
        try:
            deleted = self.collections.delete_pending(collection_id)
        except Exception as error:
            log.exception("Failed to delete collection")
            raise HttpException(500, INTERNAL_ERROR) from error
        if not deleted:
            raise HttpException(409, NOT_PENDING)

    def _find_pending(
        self, collection_id: int, owner_id: int | None = None
    ) -> CollectionRow:
        row = self._find(collection_id, owner_id)
        if row["estado"] != STATUS_PENDING:
            raise HttpException(409, NOT_PENDING)
        return row

    def _find(self, collection_id: int, owner_id: int | None = None) -> CollectionRow:
        """owner_id None = sin restriccion (admin); si no, debe ser el recolector."""
        try:
            row = self.collections.find(collection_id)
        except Exception as error:
            log.exception("Failed to fetch collection")
            raise HttpException(500, INTERNAL_ERROR) from error
        if row is None:
            raise HttpException(404, NOT_FOUND)
        if owner_id is not None and row["recolector_id"] != owner_id:
            raise HttpException(403, NOT_OWNER)
        return row


def parse_datetime(value: str, name: str) -> datetime:
    try:
        # Hora local sin zona, como la guarda la DB.
        return datetime.fromisoformat(value).replace(tzinfo=None)
    except ValueError as error:
        raise HttpException(400, f"{name} must be an ISO date-time") from error


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
