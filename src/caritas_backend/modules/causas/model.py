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
    monto_recaudado: Decimal


class Causa(CausaRecord):
    """Lo que devuelve la API: la fila mas las etiquetas derivadas del titulo."""

    clave: str
    nombre_corto: str
