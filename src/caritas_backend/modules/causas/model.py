from datetime import datetime
from decimal import Decimal
from typing import TypedDict


class CausaRecord(TypedDict):
    """A row read from the Causas table."""

    id: int
    titulo: str
    descripcion: str | None
    monto_objetivo: Decimal
    beneficiario: str | None
    responsable: str | None
    lugar: str | None
    fecha_fin: datetime | None
