import logging
from datetime import date

from ...database import Database
from ...errors import HttpException
from .model import DonorDetail, DonorRecord, RiskInfo
from .repository import DonorRepository

DAYS_GREEN = 30
DAYS_YELLOW = 60

INTERNAL_ERROR = "Internal server error"
DONOR_NOT_FOUND = "Donor not found"

log = logging.getLogger(__name__)


class DonorService:
    def __init__(self, database: Database) -> None:
        self.donors = DonorRepository(database)

    def get_detail(self, donor_id: int) -> DonorDetail:
        try:
            donor = self.donors.find_by_id(donor_id)
        except Exception as error:
            log.exception("Failed to fetch donor detail")
            raise HttpException(500, INTERNAL_ERROR) from error

        if donor is None:
            raise HttpException(404, DONOR_NOT_FOUND)

        return to_donor_detail(donor, date.today())


def to_donor_detail(donor: DonorRecord, today: date) -> DonorDetail:
    full_name = build_full_name(donor)
    last_donation_at = donor["ultima_donacion_fecha"]
    days_without_donating = (
        max((today - last_donation_at.date()).days, 0)
        if last_donation_at is not None
        else None
    )

    risk: RiskInfo = {
        "level": get_risk_level(days_without_donating),
        "months_without_donating": (
            days_without_donating // 30
            if days_without_donating is not None
            else None
        ),
        "last_donation_at": (
            last_donation_at.isoformat() if last_donation_at is not None else None
        ),
    }

    return {
        "id": donor["id"],
        "full_name": full_name,
        "initials": build_initials(full_name),
        "email": donor["email"],
        "phone": donor["telefono"],
        "neighborhood": donor["colonia"],
        "age": completed_years(donor["dia_nacimiento"].date(), today)
        if donor["dia_nacimiento"] is not None
        else None,
        "years_as_donor": completed_years(donor["fecha_creacion"].date(), today),
        "risk": risk,
        "contribution": donor["ultima_donacion_monto"],
    }


def build_full_name(donor: DonorRecord) -> str:
    return " ".join(
        part
        for part in (
            donor["nombre"],
            donor["apellido_paterno"],
            donor["apellido_materno"],
        )
        if part
    )


def build_initials(full_name: str) -> str:
    return "".join(part[0].upper() for part in full_name.split()[:2])


def completed_years(start: date, end: date) -> int:
    years = end.year - start.year
    anniversary_has_passed = (end.month, end.day) >= (start.month, start.day)
    return max(years - (not anniversary_has_passed), 0)


def get_risk_level(days_without_donating: int | None) -> str:
    if days_without_donating is not None and days_without_donating < DAYS_GREEN:
        return "green"
    if days_without_donating is not None and days_without_donating < DAYS_YELLOW:
        return "yellow"
    return "red"
