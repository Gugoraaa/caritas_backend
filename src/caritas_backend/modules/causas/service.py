import logging

from ...database import Database
from ...errors import HttpException
from .labels import with_labels
from .model import Causa
from .repository import CausaRepository

INTERNAL_ERROR = "Internal server error"
CAUSA_NOT_FOUND = "Causa not found"

log = logging.getLogger(__name__)


class CausaService:
    def __init__(self, database: Database) -> None:
        self.causas = CausaRepository(database)

    def list_all(self) -> list[Causa]:
        try:
            rows = self.causas.find_all()
        except Exception as error:
            log.exception("Failed to list causas")
            raise HttpException(500, INTERNAL_ERROR) from error

        return [with_labels(row) for row in rows]

    def get_detail(self, causa_id: int) -> Causa:
        try:
            causa = self.causas.find_by_id(causa_id)
        except Exception as error:
            log.exception("Failed to fetch causa detail")
            raise HttpException(500, INTERNAL_ERROR) from error

        if causa is None:
            raise HttpException(404, CAUSA_NOT_FOUND)

        return with_labels(causa)

    def create(self, data: dict) -> Causa:
        try:
            new_id = self.causas.insert(data)
        except Exception as error:
            log.exception("Failed to create causa")
            raise HttpException(500, INTERNAL_ERROR) from error

        return self.get_detail(new_id)

    def update(self, causa_id: int, data: dict) -> Causa:
        try:
            affected = self.causas.update(causa_id, data)
        except Exception as error:
            log.exception("Failed to update causa")
            raise HttpException(500, INTERNAL_ERROR) from error

        if affected == 0:
            raise HttpException(404, CAUSA_NOT_FOUND)

        return self.get_detail(causa_id)

    def delete(self, causa_id: int) -> None:
        try:
            affected = self.causas.delete(causa_id)
        except Exception as error:
            log.exception("Failed to delete causa")
            raise HttpException(500, INTERNAL_ERROR) from error

        if affected == 0:
            raise HttpException(404, CAUSA_NOT_FOUND)
