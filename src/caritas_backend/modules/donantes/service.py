import logging

from ...database import Database
from ...errors import HttpException
from .repository import DonanteRow, DonantesRepository, nombre_completo

INTERNAL_ERROR = "Error interno del servidor"

log = logging.getLogger(__name__)


class DonantesService:
    def __init__(self, database: Database) -> None:
        self.donantes = DonantesRepository(database)

    def list_donantes(self) -> list[dict]:
        try:
            rows = self.donantes.find_all()
        except Exception as error:
            log.exception("Fallo la consulta de donantes")
            raise HttpException(500, INTERNAL_ERROR) from error

        return [to_public_donante(row) for row in rows]


def to_public_donante(row: DonanteRow) -> dict:
    return {"id": row["id"], "nombre": nombre_completo(row)}
