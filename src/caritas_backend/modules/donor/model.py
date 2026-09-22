from datetime import datetime
from typing import Literal, TypedDict


class DonorRecord(TypedDict):
    """A row read from the Donantes table."""

    id: int
    nombre: str
    apellido_paterno: str
    apellido_materno: str | None
    apodo: str | None
    razon_social: str | None
    curp: str | None
    email: str | None
    telefono: str | None
    telefono_oficina: str | None
    dia_nacimiento: datetime | None
    fecha_creacion: datetime


class RiskInfo(TypedDict):
    """Risk information calculated from the donor's payment history."""

    level: Literal["low", "high"]
    months_without_donating: int | None
    last_donation_at: datetime | None


class DonorDetail(TypedDict):
    """Response returned for the donor detail screen."""

    id: int
    full_name: str
    initials: str
    email: str | None
    phone: str | None
    age: int | None
    years_as_donor: int
    risk: RiskInfo
    call_context: str | None
