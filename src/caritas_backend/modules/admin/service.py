import logging
from datetime import date

from ...database import Database
from ...errors import HttpException
from ..causas.labels import build_clave, build_nombre_corto
from ..donor.service import build_full_name, build_initials, days_since, get_risk_level
from .repository import AdminDonorRow, AdminRepository

INTERNAL_ERROR = "Internal server error"

RISK_LEVELS = ("green", "yellow", "red")
PAYMENT_METHODS = ("efectivo", "spei")

log = logging.getLogger(__name__)


class AdminService:
    def __init__(self, database: Database) -> None:
        self.admin = AdminRepository(database)

    def list_donors(
        self,
        search: str | None = None,
        risk: str | None = None,
        causa_id: int | None = None,
        metodo: str | None = None,
    ) -> list[dict]:
        try:
            rows = self.admin.find_donors(search, causa_id, metodo)
        except Exception as error:
            log.exception("Failed to list donors for admin")
            raise HttpException(500, INTERNAL_ERROR) from error

        # Mismo "hoy" que GET /donors/{id}, para que el riesgo coincida.
        today = date.today()
        donors = [to_admin_donor(row, today) for row in rows]
        if risk:
            donors = [donor for donor in donors if donor["risk"]["level"] == risk]
        return donors


def to_admin_donor(row: AdminDonorRow, today: date) -> dict:
    full_name = build_full_name(row)
    last_donation_at = row["ultima_donacion_fecha"]
    days_without_donating = days_since(last_donation_at, today)

    return {
        "id": row["id"],
        "full_name": full_name,
        "initials": build_initials(full_name),
        "neighborhood": row["colonia"],
        "causa": to_causa_label(row),
        "last_donation_at": (
            last_donation_at.isoformat() if last_donation_at is not None else None
        ),
        "last_donation_amount": row["ultima_donacion_monto"],
        "payment_method": row["metodo_pago"],
        "risk": {
            "level": get_risk_level(days_without_donating),
            "days_without_donating": days_without_donating,
        },
    }


def to_causa_label(row: AdminDonorRow) -> dict | None:
    if row["causa_id"] is None:
        return None
    titulo = row["causa_titulo"]
    return {
        "id": row["causa_id"],
        "titulo": titulo,
        "clave": build_clave(titulo),
        "nombre_corto": build_nombre_corto(titulo),
    }
